# Start MediaMTX container for local streaming (RTMP/WebRTC/RTSP)
# Usage: .\scripts\start_mediamtx.ps1

$ErrorActionPreference = "Stop"
$ContainerName = "home-mediamtx"
$Image = "bluenviron/mediamtx:latest"

function Find-Docker {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        return (Get-Command docker).Source
    }
    $candidates = @(
        "D:\Docker\Program\resources\bin\docker.exe",
        "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
        "$env:LOCALAPPDATA\Programs\Docker\Docker\resources\bin\docker.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$Docker = Find-Docker
if (-not $Docker) {
    Write-Host "Docker not found. Run .\scripts\setup_docker_d.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Using docker: $Docker" -ForegroundColor Cyan

# Wait for Docker engine
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    & $Docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Write-Host "Waiting for Docker engine... ($($i + 1)/30)"
    Start-Sleep -Seconds 4
}
if (-not $ready) {
    Write-Host "Docker engine not running. Start Docker Desktop and retry." -ForegroundColor Red
    exit 1
}

$existing = & $Docker ps -a --filter "name=$ContainerName" --format "{{.Names}}" 2>$null
if ($existing -eq $ContainerName) {
    Write-Host "Removing old container..."
    & $Docker rm -f $ContainerName | Out-Null
}

Write-Host "Starting MediaMTX..." -ForegroundColor Cyan
& $Docker run -d `
    --name $ContainerName `
    --restart=always `
    -p 9090:1935 `
    -p 8554:8554 `
    -p 8889:8889 `
    -p 8189:8189/udp `
    -e MTX_WEBRTCADDITIONALHOSTS=127.0.0.1 `
    $Image

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start MediaMTX." -ForegroundColor Red
    exit 1
}

& $Docker ps --filter "name=$ContainerName"
Write-Host @"

MediaMTX is running.

  OBS server : rtmp://127.0.0.1:9090/stream
  Stream key : 1 (living room) / 2 (kitchen)
  WebRTC     : http://127.0.0.1:8889/stream/1/
  RTSP (AI)  : rtsp://127.0.0.1:8554/stream/1

"@ -ForegroundColor Green
