# Start Vite dev server (Windows)
# Usage: .\scripts\start_frontend.ps1

$ErrorActionPreference = "Stop"
$Frontend = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"

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
