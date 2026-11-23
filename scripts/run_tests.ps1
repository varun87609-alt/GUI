# Automated Test Suite Runner for OpenFOAM AutoMesh
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Running OpenFOAM AutoMesh Complete Test Suite  " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Backend Tests (Pytest)
Write-Host "`n>>> Running Backend Unit and Integration Tests..." -ForegroundColor Yellow
python -m pytest backend/tests -v
$backendExit = $LASTEXITCODE

# 2. Frontend Tests (Vitest)
Write-Host "`n>>> Running Frontend Component & Service Tests..." -ForegroundColor Yellow
Push-Location frontend
npx vitest run
$frontendExit = $LASTEXITCODE
Pop-Location

Write-Host "`n=================================================" -ForegroundColor Cyan
Write-Host "  Test Execution Summary                         " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

if ($backendExit -eq 0 -and $frontendExit -eq 0) {
    Write-Host "ALL TESTS PASSED! Backend: OK | Frontend: OK" -ForegroundColor Green
} else {
    Write-Host "TESTS FAILED. Backend Exit Code: $backendExit, Frontend Exit Code: $frontendExit" -ForegroundColor Red
}
