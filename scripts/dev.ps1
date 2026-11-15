# Development Server Script for FORGE AI
# Starts all three services in parallel

$ErrorActionPreference = "Stop"

Write-Host "=== FORGE AI Development Server ===" -ForegroundColor Cyan

# Start Backend
Write-Host "`nStarting Backend API..." -ForegroundColor Yellow
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/api; .\venv\Scripts\Activate.ps1; python run.py" -PassThru
Write-Host "  Backend PID: $($backend.Id)" -ForegroundColor Green

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Yellow
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd apps/web; npm run dev" -PassThru
Write-Host "  Frontend PID: $($frontend.Id)" -ForegroundColor Green

# Start Local Agent
Write-Host "Starting Local Agent..." -ForegroundColor Yellow
$agent = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/local-agent; .\venv\Scripts\Activate.ps1; python run.py" -PassThru
Write-Host "  Local Agent PID: $($agent.Id)" -ForegroundColor Green

Write-Host "`n=== All Services Started ===" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API: http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop all services" -ForegroundColor Yellow

try {
    Wait-Process -Id $backend.Id, $frontend.Id, $agent.Id
} finally {
    Write-Host "`nStopping all services..." -ForegroundColor Yellow
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $agent.Id -Force -ErrorAction SilentlyContinue
    Write-Host "All services stopped." -ForegroundColor Green
}
