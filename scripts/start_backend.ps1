# Start Django dev server (Windows)
# Usage: .\scripts\start_backend.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvName = "home-camera"
$Port = if ($env:DJANGO_PORT) { $env:DJANGO_PORT } else { "8000" }

function Find-Conda {
    if (Get-Command conda -ErrorAction SilentlyContinue) {
        return (Get-Command conda).Source
    }
    foreach ($path in @(
        "$env:USERPROFILE\anaconda3\Scripts\conda.exe",
        "$env:USERPROFILE\miniconda3\Scripts\conda.exe",
        "D:\Anaconda\Scripts\conda.exe"
    )) {
        if (Test-Path $path) { return $path }
    }
    return $null
}

$Conda = Find-Conda
if (-not $Conda) {
    Write-Host "conda not found. Run setup first: .\scripts\setup_backend.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "Starting Django on http://127.0.0.1:$Port (env: $EnvName)" -ForegroundColor Cyan
Push-Location $Backend
try {
    & $Conda run -n $EnvName --no-capture-output python manage.py runserver $Port
} finally {
    Pop-Location
}
