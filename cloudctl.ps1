# USPC cloudctl Windows PowerShell execution wrapper
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

if (Test-Path "C:\Program Files\RedHat\Podman\podman.exe") {
    if ($Env:Path -notmatch "RedHat\\Podman") {
        $Env:Path = "C:\Program Files\RedHat\Podman;$Env:Path"
    }
}

# Auto-start Podman machine if stopped
if (Get-Command podman -ErrorAction SilentlyContinue) {
    $mList = podman machine list 2>$null
    if ($mList -match "podman-machine-default" -and $mList -notmatch "Currently running") {
        Write-Host "==> Podman VM is stopped. Starting Podman machine..." -ForegroundColor Cyan
        podman machine start
    }
}

$PythonExe = "python"
if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonExe = "$ScriptDir\.venv\Scripts\python.exe"
}

& $PythonExe -m cloudctl $args
