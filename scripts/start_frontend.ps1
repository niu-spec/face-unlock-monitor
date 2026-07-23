# Start Vite dev server (Windows)
# Usage: .\scripts\start_frontend.ps1

$ErrorActionPreference = "Stop"
$Frontend = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"

$EnvDev = Join-Path $Frontend ".env.development"
$EnvExample = Join-Path $Frontend ".env.development.example"
if (-not (Test-Path $EnvDev) -and (Test-Path $EnvExample)) {
    Copy-Item $EnvExample $EnvDev
    Write-Host "Created frontend/.env.development from example." -ForegroundColor Yellow
}

if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    Push-Location $Frontend
    try { npm install } finally { Pop-Location }
}

Write-Host "Starting frontend on http://localhost:5173" -ForegroundColor Cyan
Push-Location $Frontend
try {
    npm run dev
} finally {
    Pop-Location
}
