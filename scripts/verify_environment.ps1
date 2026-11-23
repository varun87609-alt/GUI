# Environment Verification Script for OpenFOAM AutoMesh
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  OpenFOAM AutoMesh - Environment Verification   " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$allOk = $true

# 1. Check Python
Write-Host "`n[1/5] Checking Python installation..." -NoNewline
try {
    $pyVersion = python --version 2>&1
    Write-Host " OK ($pyVersion)" -ForegroundColor Green
} catch {
    Write-Host " FAILED. Python not found." -ForegroundColor Red
    $allOk = $false
}

# 2. Check Node & NPM
Write-Host "[2/5] Checking Node.js and NPM..." -NoNewline
try {
    $nodeVersion = node --version 2>&1
    $npmVersion = npm --version 2>&1
    Write-Host " OK (Node $nodeVersion, NPM $npmVersion)" -ForegroundColor Green
} catch {
    Write-Host " FAILED. Node.js or NPM not found." -ForegroundColor Red
    $allOk = $false
}

# 3. Check Docker Daemon
Write-Host "[3/5] Checking Docker Desktop daemon..." -NoNewline
try {
    $dockerInfo = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " OK (Docker daemon connected)" -ForegroundColor Green
    } else {
        Write-Host " FAILED. Docker daemon not running." -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host " FAILED. Docker CLI not found." -ForegroundColor Red
    $allOk = $false
}

# 4. Check OpenFOAM Image
Write-Host "[4/5] Checking OpenFOAM Docker image (openeuler/openfoam:2506-oe2403sp4)..." -NoNewline
try {
    $images = docker images "openeuler/openfoam:2506-oe2403sp4" -q
    if ($images) {
        Write-Host " OK (Image ID: $images)" -ForegroundColor Green
    } else {
        Write-Host " FAILED. Image openeuler/openfoam:2506-oe2403sp4 not found locally." -ForegroundColor Red
        Write-Host "       Run: docker pull openeuler/openfoam:2506-oe2403sp4" -ForegroundColor Yellow
        $allOk = $false
    }
} catch {
    Write-Host " FAILED." -ForegroundColor Red
    $allOk = $false
}

# 5. Verify OpenFOAM Utilities inside Container
Write-Host "[5/5] Verifying OpenFOAM utilities in container sandbox..." -NoNewline
try {
    $probe = docker run --rm --entrypoint /bin/bash openeuler/openfoam:2506-oe2403sp4 -c "source /opt/OpenFOAM-v2506/etc/bashrc && which blockMesh snappyHexMesh surfaceCheck surfaceFeatureExtract checkMesh && echo FOAM_OK" 2>&1
    if ($probe -match "FOAM_OK") {
        Write-Host " OK (blockMesh, snappyHexMesh, checkMesh verified)" -ForegroundColor Green
    } else {
        Write-Host " FAILED. Could not execute OpenFOAM utilities inside container." -ForegroundColor Red
        $allOk = $false
    }
} catch {
    Write-Host " FAILED." -ForegroundColor Red
    $allOk = $false
}

Write-Host "`n-------------------------------------------------"
if ($allOk) {
    Write-Host "ALL CHECKS PASSED! Your environment is ready." -ForegroundColor Green
} else {
    Write-Host "SOME CHECKS FAILED. Please review the errors above." -ForegroundColor Red
}
Write-Host "-------------------------------------------------"
