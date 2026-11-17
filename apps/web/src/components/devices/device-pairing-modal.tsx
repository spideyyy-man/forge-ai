"use client";

import React, { useEffect, useState } from "react";
import { useDeviceStore } from "@/stores/device-store";
import { useUIStore } from "@/stores/ui-store";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Laptop, CheckCircle, Copy, AlertCircle, RefreshCw, Loader2, Trash2 } from "lucide-react";

export const DevicePairingModal = () => {
  const { isPairingDialogOpen, setIsPairingDialogOpen } = useUIStore();
  const { registerDevice, isLoading, devices, fetchDevices, revokeDevice } = useDeviceStore();
  const [deviceName, setDeviceName] = useState("Local-Machine");
  const [generatedPairingCode, setGeneratedPairingCode] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  // Load the device list whenever the dialog opens, so existing/stale devices show.
  useEffect(() => {
    if (isPairingDialogOpen) fetchDevices();
  }, [isPairingDialogOpen, fetchDevices]);

  // After a code is shown, poll the device until the agent actually connects — this
  // turns the blind copy-paste-and-hope into a confirmed "Agent connected".
  useEffect(() => {
    if (!deviceId || connected) return;
    let stop = false;
    const tick = async () => {
      try {
        const d = await api.getDevice(deviceId);
        if (!stop && d.is_connected) {
          setConnected(true);
          fetchDevices();
        }
      } catch {
        /* keep polling */
      }
    };
    const id = setInterval(tick, 2500);
    tick();
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [deviceId, connected, fetchDevices]);

  if (!isPairingDialogOpen) return null;

  // Absolute path (from .env.local) so the command runs from ANY directory. Falls back to
  // the repo-root-relative path if the env var isn't set.
  const agentScript = process.env.NEXT_PUBLIC_AGENT_SCRIPT || "scripts\\run-agent.ps1";
  // Repo-relative agent dir for the manual fallback, derived from the script path.
  const agentDir = agentScript.replace(/[\\/]scripts[\\/]run-agent\.ps1$/i, "\\services\\local-agent");
  const runCommand =
    generatedPairingCode && deviceId
      ? `powershell -ExecutionPolicy Bypass -File "${agentScript}" -PairingCode ${generatedPairingCode} -DeviceId ${deviceId}`
      : "";

  const handleCopyCommand = () => {
    if (runCommand) {
      navigator.clipboard.writeText(runCommand);
      setCopiedCmd(true);
      setTimeout(() => setCopiedCmd(false), 2000);
    }
  };

  const handleGenerateCode = async () => {
    setError(null);
    try {
      const dev = await registerDevice(deviceName, "WINDOWS");
      setGeneratedPairingCode(dev.pairing_code || "PENDING");
      setDeviceId(dev.id);
    } catch (err: any) {
      setError(err.message || "Failed to generate pairing code");
    }
  };

  const handleCopy = () => {
    if (generatedPairingCode) {
      navigator.clipboard.writeText(generatedPairingCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleClose = () => {
    setIsPairingDialogOpen(false);
    setGeneratedPairingCode(null);
    setDeviceId(null);
    setError(null);
    setConnected(false);
  };

  const handleRevoke = async (id: string, name: string) => {
    if (!window.confirm(`Revoke "${name}"? The agent on that machine will be disconnected and must be paired again.`)) return;
    try {
      await revokeDevice(id);
    } catch (err: any) {
      setError(err.message || "Could not revoke device.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <Card className="w-full max-w-md border-[#2a2a44] bg-[#12121a] shadow-2xl">
        <CardHeader className="border-b border-[#202035]">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
              <Laptop className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold">Pair Local Workspace Agent</CardTitle>
              <CardDescription>Connect a Windows agent to enable file access & terminal operations</CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-5">
          {error && (
            <div className="flex items-center gap-2 p-3 text-xs rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!generatedPairingCode ? (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-400 font-medium block mb-1">Device Label</label>
                <input
                  type="text"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder="e.g. My-Windows-Workstation"
                  className="w-full text-sm bg-[#181824] border border-[#26263d] rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <p className="text-xs text-slate-400">
                Clicking generate will create an authenticated 6-character registration token for your local CLI agent.
              </p>

              {devices.filter((d) => d.status !== "REVOKED").length > 0 && (
                <div className="pt-1">
                  <p className="text-[11px] font-medium text-slate-400 mb-1.5">Paired devices</p>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto">
                    {devices
                      .filter((d) => d.status !== "REVOKED")
                      .map((d) => (
                        <div key={d.id} className="flex items-center justify-between gap-2 text-xs rounded-lg bg-[#151522] px-2.5 py-1.5">
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                                d.is_connected ? "bg-emerald-400" : d.status === "ACTIVE" ? "bg-amber-400" : "bg-slate-500"
                              }`}
                              title={d.is_connected ? "Connected" : d.status}
                            />
                            <span className="truncate text-slate-200">{d.name}</span>
                            <span className="text-[10px] text-slate-500 shrink-0">
                              {d.is_connected ? "connected" : d.status.toLowerCase()}
                            </span>
                          </div>
                          <button
                            onClick={() => handleRevoke(d.id, d.name)}
                            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-rose-400 transition shrink-0"
                            title="Revoke this device"
                          >
                            <Trash2 className="h-3 w-3" /> Revoke
                          </button>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-center p-4 rounded-xl bg-[#181826] border border-[#262640]">
                <p className="text-xs text-slate-400 mb-1">Your Pairing Code</p>
                <div className="text-3xl font-mono font-bold tracking-widest text-indigo-400 mb-2">
                  {generatedPairingCode}
                </div>
                <Button variant="outline" size="sm" onClick={handleCopy} className="text-xs h-7">
                  {copied ? (
                    <>
                      <CheckCircle className="h-3.5 w-3.5 text-emerald-400 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5 mr-1" />
                      Copy Code
                    </>
                  )}
                </Button>
              </div>

              {/* Live pairing result — polls the backend so the user gets real confirmation. */}
              {connected ? (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs">
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  <span>Agent connected — you&apos;re all set. You can close this.</span>
                </div>
              ) : (
                <div className="flex items-center justify-center gap-2 text-[11px] text-slate-400">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" /> Waiting for the agent to connect…
                </div>
              )}

              <div className="text-xs text-slate-400 space-y-2 bg-surface-elevated p-3 rounded-lg border border-border">
                <div className="flex items-center justify-between">
                  <p className="font-semibold text-slate-300">Run in any PowerShell window to pair & connect:</p>
                  <button
                    onClick={handleCopyCommand}
                    className="flex items-center gap-1 text-[11px] text-ember-hot hover:text-ember transition"
                  >
                    {copiedCmd ? (
                      <>
                        <CheckCircle className="h-3 w-3 text-emerald-400" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3" /> Copy command
                      </>
                    )}
                  </button>
                </div>
                <code className="block font-mono bg-black/40 p-2 rounded text-ember-hot select-all overflow-x-auto text-[11px] whitespace-pre-wrap break-all">
                  {runCommand}
                </code>
                <p className="text-[11px] text-slate-500">
                  This starts the agent, no manual <span className="font-mono">cd</span> needed. It stays running — keep the
                  window open. First launch is slow (~40s) while the agent loads.
                </p>
                <details className="text-[11px] text-slate-500">
                  <summary className="cursor-pointer hover:text-slate-400">Prefer to run it manually?</summary>
                  <code className="block font-mono bg-black/40 p-2 rounded text-slate-300 select-all overflow-x-auto mt-1.5">
                    cd "{agentDir}"{"\n"}.\venv\Scripts\python.exe run.py --pair {generatedPairingCode} --device-id {deviceId}
                  </code>
                </details>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex justify-end gap-2 border-t border-[#202035] pt-4">
          <Button variant="ghost" size="sm" onClick={handleClose}>
            Close
          </Button>
          {!generatedPairingCode ? (
            <Button size="sm" onClick={handleGenerateCode} disabled={isLoading || !deviceName.trim()}>
              {isLoading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1" />
                  Generating...
                </>
              ) : (
                "Generate Code"
              )}
            </Button>
          ) : (
            <Button size="sm" onClick={handleClose}>
              Done
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
};
