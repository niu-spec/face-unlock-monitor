# Backend setup (Windows + conda)
# Usage: .\scripts\setup_backend.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvName = "home-camera"

function Find-Conda {
    if (Get-Command conda -ErrorAction SilentlyContinue) {
        return (Get-Command conda).Source
    }
    $candidates = @(
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "D:\Anaconda\Scripts\conda.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

$Conda = Find-Conda
if (-not $Conda) {
    Write-Host "conda not found. Install Anaconda/Miniconda first." -ForegroundColor Red
    exit 1
}

Write-Host "conda: $Conda" -ForegroundColor Cyan
Write-Host "env:   $EnvName" -ForegroundColor Cyan

$envList = & $Conda env list 2>&1 | Out-String
if ($envList -match "\s$EnvName\s") {
    Write-Host "Updating existing env..." -ForegroundColor Yellow
    & $Conda env update -n $EnvName -f (Join-Path $Backend "environment.yml") --prune
} else {
    Write-Host "Creating env..." -ForegroundColor Yellow
    & $Conda env create -f (Join-Path $Backend "environment.yml")
}

Write-Host ""
Write-Host "Verifying dlib / face_recognition / Django..." -ForegroundColor Cyan
& $Conda run -n $EnvName python (Join-Path $Root "scripts\verify_backend.py")

Push-Location $Backend
try {
    & $Conda run -n $EnvName python manage.py check
    & $Conda run -n $EnvName python manage.py test apps.face.tests -v 0
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Start backend:" -ForegroundColor Green
Write-Host "  .\scripts\start_backend.ps1"
Write-Host "  # or: conda activate $EnvName && cd backend && python manage.py runserver 8000"
