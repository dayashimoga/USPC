# Windows PowerShell automated installation script for USPC
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

Write-Host "==> USPC Windows Setup (WSL2 / Podman Machine / Docker)" -ForegroundColor Cyan

# Check Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3 is required. Please install Python 3.10+."
    exit 1
}

# Run cloudctl
& python -m cloudctl init
& python -m cloudctl install $args
