# Reset MySQL root password (run as Administrator)
# Usage: Right-click PowerShell -> Run as administrator -> run this script

$MyIni = "C:\ProgramData\MySQL\MySQL Server 9.6\my.ini"
$InitSqlWin = "C:\ProgramData\MySQL\MySQL Server 9.6\reset-root-init.sql"
$InitSqlIni = "C:/ProgramData/MySQL/MySQL Server 9.6/reset-root-init.sql"
$NewPassword = "changeme"
$ServiceName = "MySQL96"
$MysqlExe = "C:\Program Files\MySQL\MySQL Server 9.6\bin\mysql.exe"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Wait-ServiceState($name, $state, $seconds = 30) {
    for ($i = 0; $i -lt $seconds; $i++) {
        if ((Get-Service $name -ErrorAction SilentlyContinue).Status -eq $state) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

if (-not (Test-IsAdmin)) {
    Write-Host "ERROR: Please run PowerShell as Administrator." -ForegroundColor Red
    Write-Host "Right-click PowerShell -> Run as administrator" -ForegroundColor Yellow
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "==> Stop MySQL service (if running)..." -ForegroundColor Cyan
$svc = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $svc) {
    Write-Host "ERROR: Service $ServiceName not found." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}
if ($svc.Status -eq "Running") {
    Stop-Service $ServiceName -Force
    Wait-ServiceState $ServiceName "Stopped" | Out-Null
    Write-Host "    stopped" -ForegroundColor Green
} else {
    Write-Host "    already stopped" -ForegroundColor Yellow
}

Write-Host "==> Write init SQL file..." -ForegroundColor Cyan
Set-Content -Path $InitSqlWin -Value "ALTER USER 'root'@'localhost' IDENTIFIED BY '$NewPassword';" -Encoding ASCII

Write-Host "==> Backup and patch my.ini..." -ForegroundColor Cyan
Copy-Item $MyIni "$MyIni.bak" -Force
$iniContent = Get-Content $MyIni -Raw
if ($iniContent -notmatch 'init-file=') {
    $iniContent = $iniContent -replace '\[mysqld\]', "[mysqld]`r`ninit-file=$InitSqlIni"
    Set-Content -Path $MyIni -Value $iniContent -Encoding ASCII
    Write-Host "    init-file added" -ForegroundColor Green
}

Write-Host "==> Start MySQL (runs password reset once)..." -ForegroundColor Cyan
Start-Service $ServiceName
Wait-ServiceState $ServiceName "Running" 20 | Out-Null
Start-Sleep -Seconds 5

Write-Host "==> Restore my.ini..." -ForegroundColor Cyan
Copy-Item "$MyIni.bak" $MyIni -Force
Remove-Item "$MyIni.bak" -Force
Remove-Item $InitSqlWin -Force -ErrorAction SilentlyContinue

Write-Host "==> Restart MySQL..." -ForegroundColor Cyan
Restart-Service $ServiceName -Force
Wait-ServiceState $ServiceName "Running" 20 | Out-Null
Start-Sleep -Seconds 3

Write-Host "==> Verify password and create database..." -ForegroundColor Cyan
$env:MYSQL_PWD = $NewPassword
& $MysqlExe -u root -e "CREATE DATABASE IF NOT EXISTS home_camera_monitor CHARACTER SET utf8mb4;"
$ok = $LASTEXITCODE -eq 0
Remove-Item Env:MYSQL_PWD -ErrorAction SilentlyContinue

if ($ok) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Password reset OK" -ForegroundColor Green
    Write-Host " Password: $NewPassword" -ForegroundColor Green
    Write-Host " Database: home_camera_monitor" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next in backend folder:" -ForegroundColor Cyan
    Write-Host "  conda activate home-camera"
    Write-Host '  $env:DB_PASSWORD = "changeme"'
    Write-Host "  python manage.py migrate"
    Write-Host "  python manage.py runserver 8000"
} else {
    Write-Host "Verification failed." -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to close"
