# Cleanup Script for OpenFOAM AutoMesh
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  Cleaning Stale Workspace Data & Containers     " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot

# 1. Clean old jobs directory if requested
$jobsDir = Join-Path $rootDir "workspace_jobs\jobs"
if (Test-Path $jobsDir) {
    Write-Host "Found job workspaces in $jobsDir."
    $confirm = Read-Host "Do you want to clear old job working directories? (y/N)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Get-ChildItem -Path $jobsDir -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
        Write-Host "Cleared job directories." -ForegroundColor Green
    }
}

# 2. Clean temporary pytest cache
$pyCache = Join-Path $rootDir ".pytest_cache"
if (Test-Path $pyCache) {
    Remove-Item -Recurse -Force $pyCache -ErrorAction SilentlyContinue
    Write-Host "Removed .pytest_cache." -ForegroundColor Green
}

Write-Host "Cleanup complete." -ForegroundColor Green
