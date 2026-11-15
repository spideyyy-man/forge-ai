# Development Setup Script for FORGE AI
# Run this from the forge-ai root directory

$ErrorActionPreference = "Stop"

Write-Host "=== FORGE AI Development Setup ===" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

$nodeVersion = node --version 2>$null
if ($nodeVersion) {
    Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green
} else {
    Write-Host "  Node.js: NOT FOUND - Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version 2>$null
if ($pythonVersion) {
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  Python: NOT FOUND - Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

$gitVersion = git --version 2>$null
if ($gitVersion) {
    Write-Host "  Git: $gitVersion" -ForegroundColor Green
} else {
    Write-Host "  Git: NOT FOUND - Please install Git" -ForegroundColor Red
    exit 1
}

# Setup Frontend
Write-Host "`nSetting up Frontend..." -ForegroundColor Yellow
Push-Location apps/web
if (-not (Test-Path node_modules)) {
    npm install
}
Pop-Location
Write-Host "  Frontend ready" -ForegroundColor Green

# Setup Backend
Write-Host "`nSetting up Backend..." -ForegroundColor Yellow
Push-Location apps/api
if (-not (Test-Path venv)) {
    python -m venv venv
}
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "  Created .env from template - please edit with your settings" -ForegroundColor Yellow
}
deactivate
Pop-Location
Write-Host "  Backend ready" -ForegroundColor Green

# Setup Local Agent
Write-Host "`nSetting up Local Agent..." -ForegroundColor Yellow
Push-Location services/local-agent
if (-not (Test-Path venv)) {
    python -m venv venv
}
& .\venv\Scripts\Activate.ps1
pip install -r requirements.txt -q
deactivate
Pop-Location
Write-Host "  Local Agent ready" -ForegroundColor Green

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Run '.\scripts\dev.ps1' to start all services" -ForegroundColor White
