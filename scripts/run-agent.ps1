# FORGE AI — Local Agent launcher
#
# Pairs (first time) and runs the local workspace agent without any manual `cd`
# or venv activation. Run from anywhere inside the repo.
#
#   First time (values come from the web "Connect Agent" dialog):
#     powershell -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -PairingCode 4B132B -DeviceId 337108b2-...
#
#   After pairing (credentials are saved encrypted, just reconnect):
#     powershell -ExecutionPolicy Bypass -File scripts\run-agent.ps1

param(
    [string]$PairingCode,
    [string]$DeviceId,
    [string]$Api = "http://localhost:8000/api",
    [string]$Server
)

$ErrorActionPreference = "Stop"

$agentDir = Join-Path $PSScriptRoot "..\services\local-agent"
if (-not (Test-Path $agentDir)) {
    Write-Host "Could not find services\local-agent next to this script." -ForegroundColor Red
    exit 1
}
Set-Location $agentDir

# Prefer the project venv's Python; fall back to whatever `python` is on PATH.
$py = Join-Path $agentDir "venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Agent venv not found; using 'python' from PATH. Run scripts\setup.ps1 first for an isolated env." -ForegroundColor Yellow
    $py = "python"
}

$agentArgs = @("run.py")
if ($PairingCode) { $agentArgs += @("--pair", $PairingCode) }
if ($DeviceId)    { $agentArgs += @("--device-id", $DeviceId) }
if ($Api)         { $agentArgs += @("--api", $Api) }
if ($Server)      { $agentArgs += @("--server", $Server) }

if ($PairingCode) {
    Write-Host "Pairing and starting the FORGE AI local agent..." -ForegroundColor Cyan
} else {
    Write-Host "Starting the FORGE AI local agent (using saved credentials)..." -ForegroundColor Cyan
}

& $py @agentArgs
