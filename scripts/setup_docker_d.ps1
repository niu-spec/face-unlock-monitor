# Install Docker Desktop to D:\Docker (requires Administrator)
# Usage: Right-click PowerShell -> Run as Administrator, then:
#   .\scripts\setup_docker_d.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$DockerRoot = "D:\Docker"
$InstallerDir = Join-Path $DockerRoot "install"
$InstallerPath = Join-Path $InstallerDir "Docker Desktop Installer.exe"
$InstallerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = [Security.Principal.WindowsPrincipal]$id
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Re-launching as Administrator..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $Root "scripts\setup_docker_d.ps1")
    )
    exit 0
}

Write-Host "=== Docker Desktop install to $DockerRoot ===" -ForegroundColor Cyan

foreach ($d in @($InstallerDir, "$DockerRoot\Program", "$DockerRoot\wsl", "$DockerRoot\windows-data")) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

if (-not (Test-Path $InstallerPath)) {
    Write-Host "Downloading Docker Desktop installer (~600MB)..." -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $InstallerUrl -OutFile $InstallerPath -UseBasicParsing
    Write-Host "Download complete." -ForegroundColor Green
} else {
    Write-Host "Installer already exists: $InstallerPath"
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Docker CLI already available. Skipping install." -ForegroundColor Green
    docker version
    exit 0
}

Write-Host "Installing Docker Desktop (may take several minutes)..." -ForegroundColor Yellow
$args = @(
    "install",
    "--accept-license",
    "--quiet",
    "--backend=wsl-2",
    "--installation-dir=$DockerRoot\Program",
    "--wsl-default-data-root=$DockerRoot\wsl",
    "--windows-containers-default-data-root=$DockerRoot\windows-data"
)

$proc = Start-Process -FilePath $InstallerPath -ArgumentList $args -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host "Installer exit code: $($proc.ExitCode)" -ForegroundColor Red
    exit $proc.ExitCode
}

Write-Host "Docker Desktop installed." -ForegroundColor Green
Write-Host "Starting Docker Desktop..."
$desktopExe = Join-Path $DockerRoot "Program\Docker Desktop.exe"
if (Test-Path $desktopExe) {
    Start-Process $desktopExe
} else {
    $fallback = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $fallback) { Start-Process $fallback }
}

Write-Host @"

Next steps:
  1. Wait for Docker Desktop tray icon to show 'Engine running'
  2. Run: .\scripts\start_mediamtx.ps1
  3. Configure OBS: rtmp://127.0.0.1:9090/stream  key=1

"@ -ForegroundColor Cyan
