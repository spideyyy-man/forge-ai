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

# Preflight: confirm the agent's Python dependencies import, so pairing doesn't fail
# later with a cryptic ImportError (common when falling back to a bare python).
$depCheck = & $py -c "import websockets, aiohttp, cryptography" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "The local agent's Python dependencies are missing or broken:" -ForegroundColor Red
    Write-Host "  $depCheck" -ForegroundColor DarkYellow
    Write-Host "Set up the agent environment, then retry:" -ForegroundColor Yellow
    Write-Host "  cd `"$agentDir`"" -ForegroundColor Gray
    Write-Host "  python -m venv venv" -ForegroundColor Gray
    Write-Host "  .\venv\Scripts\python.exe -m pip install -r requirements.txt" -ForegroundColor Gray
    Write-Host "(or run scripts\setup.ps1 from the repo root)" -ForegroundColor Gray
    exit 1
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
