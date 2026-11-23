# Launch OpenFOAM AutoMesh Development Servers
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Starting OpenFOAM AutoMesh Web Application     " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot

Write-Host "Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rootDir'; python backend/run_backend.py"

Write-Host "Starting Vite Frontend on http://127.0.0.1:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$rootDir\frontend'; npm run dev"

Write-Host "`nServers launched in separate PowerShell windows!" -ForegroundColor Cyan
Write-Host "Open your browser at: http://127.0.0.1:5173" -ForegroundColor Yellow
