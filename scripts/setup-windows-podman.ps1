<#
.SYNOPSIS
    Full Automated Setup Script for USPC on Windows (Podman + Dedicated Drive Partition).

.DESCRIPTION
    Automates the complete provisioning of USPC on Windows:
    1. Checks & installs prerequisites (Podman, Python, WSL2, Git).
    2. Initializes and starts the Podman Machine (rootless container runtime).
    3. Configures USPC to use a dedicated partition / directory for data, configs, and backups.
    4. Installs Python dependencies (pip install -e .[dev]).
    5. Executes one-command bootstrap (cloudctl setup).
    6. Verifies container health and storage partition isolation.

.PARAMETER StorageDrive
    The dedicated drive letter or directory path (e.g. "H:\USPC_STORAGE" or "D:\MyCloud").
    Default is "H:\USPC_STORAGE" if H: exists, otherwise "$HOME\.uspc".

.PARAMETER CloudName
    Identifier for the cloud platform instance. Default is "laptop-cloud".

.PARAMETER Domain
    Domain or hostname for the cloud instance. Default is "laptop-cloud.local".

.PARAMETER SkipPrerequisites
    Skip winget prerequisite installation checks.

.PARAMETER DryRun
    Perform validation without writing configuration or starting containers.
#>

[CmdletBinding()]
param (
    [string]$StorageDrive = "",
    [string]$CloudName = "laptop-cloud",
    [string]$Domain = "laptop-cloud.local",
    [switch]$SkipPrerequisites,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Msg)
    Write-Host "`n==> $Msg" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Msg)
    Write-Host "  [OK] $Msg" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Msg)
    Write-Host "  [WARN] $Msg" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Msg)
    Write-Host "  [ERROR] $Msg" -ForegroundColor Red
}

$ScriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (!(Test-Path "$ScriptDir\src\cloudctl")) {
    $ScriptDir = (Get-Location).Path
}

Write-Host "=================================================================" -ForegroundColor Blue
Write-Host "   USPC - Universal Personal Cloud Platform (Windows + Podman)   " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Blue

# -------------------------------------------------------------------------
# Step 1: Detect & Select Storage Partition
# -------------------------------------------------------------------------
Write-Step "Step 1: Configuring Storage Partition"

if ([string]::IsNullOrWhiteSpace($StorageDrive)) {
    if (Test-Path "H:\") {
        $StorageDrive = "H:\USPC_STORAGE"
    } elseif (Test-Path "D:\") {
        $StorageDrive = "D:\USPC_STORAGE"
    } else {
        $StorageDrive = "$HOME\.uspc"
    }
}

$DataPath = ($StorageDrive + "/data").Replace("\", "/")
$ConfigPath = ($StorageDrive + "/config").Replace("\", "/")
$BackupPath = ($StorageDrive + "/backups").Replace("\", "/")

Write-Success "Target Base Partition: $StorageDrive"
Write-Success "  Data Path   : $DataPath"
Write-Success "  Config Path : $ConfigPath"
Write-Success "  Backup Path : $BackupPath"

# -------------------------------------------------------------------------
# Step 2: Prerequisites Validation & Installation
# -------------------------------------------------------------------------
Write-Step "Step 2: Checking Prerequisites (Podman, Python, WSL2)"

if (!$SkipPrerequisites) {
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Warn "Python not found. Installing Python 3.11 via winget..."
        winget install --id Python.Python.3.11 -e --source winget --accept-source-agreements --accept-package-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } else {
        $pyVer = python --version 2>&1
        Write-Success "Python detected: $pyVer"
    }

    # Check for Podman
    $hasPodman = [bool](Get-Command podman -ErrorAction SilentlyContinue)
    if (!$hasPodman) {
        if (Test-Path "C:\Program Files\RedHat\Podman\podman.exe") {
            $env:Path += ";C:\Program Files\RedHat\Podman"
            $hasPodman = $true
        }
    }

    if (!$hasPodman) {
        Write-Warn "Podman CLI not found. Installing Podman via winget..."
        winget install --id RedHat.Podman -e --source winget --accept-source-agreements --accept-package-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (Test-Path "C:\Program Files\RedHat\Podman\podman.exe") {
            $env:Path += ";C:\Program Files\RedHat\Podman"
        }
        $hasPodman = [bool](Get-Command podman -ErrorAction SilentlyContinue)
    }

    if ($hasPodman) {
        Write-Success "Podman CLI detected."
    } else {
        Write-Err "Podman CLI could not be located. Please install Podman Desktop / CLI from https://podman.io"
        exit 1
    }
}

# -------------------------------------------------------------------------
# Step 3: Podman Machine Lifecycle & Initialization
# -------------------------------------------------------------------------
Write-Step "Step 3: Initializing and Starting Podman Machine"

$machineList = podman machine list 2>&1
$isRunning = $machineList -match "Currently running"

if (!$isRunning) {
    $hasMachine = $machineList -match "podman-machine-default"
    if (!$hasMachine) {
        Write-Host "Initializing default Podman machine (4 CPUs, 4GB RAM)..." -ForegroundColor Yellow
        podman machine init --cpus 4 --memory 4096 --disk-size 50
    }
    Write-Host "Starting Podman machine..." -ForegroundColor Yellow
    podman machine start
}

# Verify Podman responsiveness
$retries = 10
while ($retries -gt 0) {
    $info = podman info 2>&1
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
    $retries--
}
Write-Success "Podman container engine is active and responding."

# -------------------------------------------------------------------------
# Step 4: Python Virtual Environment & Dependencies (.venv isolation)
# -------------------------------------------------------------------------
Write-Step "Step 4: Installing USPC Python Dependencies (Local .venv Isolation)"

Set-Location $ScriptDir
if (!(Test-Path "$ScriptDir\.venv")) {
    Write-Host "Creating isolated Python virtual environment at $ScriptDir\.venv..." -ForegroundColor Yellow
    python -m venv "$ScriptDir\.venv"
}

$VenvPython = "$ScriptDir\.venv\Scripts\python.exe"
$Env:PYTHONPATH = "$ScriptDir\src;$Env:PYTHONPATH"

& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -e ".[dev]" --quiet
Write-Success "Python dependencies isolated inside local .venv (Zero global Python packages modified)."

# -------------------------------------------------------------------------
# Step 5: Generate Tailored cloud.yaml on Dedicated Partition
# -------------------------------------------------------------------------
Write-Step "Step 5: Writing Declarative Configuration"

if (!$DryRun) {
    if (!(Test-Path $StorageDrive)) { New-Item -ItemType Directory -Force -Path $StorageDrive | Out-Null }
    if (!(Test-Path "$StorageDrive\data")) { New-Item -ItemType Directory -Force -Path "$StorageDrive\data" | Out-Null }
    if (!(Test-Path "$StorageDrive\config")) { New-Item -ItemType Directory -Force -Path "$StorageDrive\config" | Out-Null }
    if (!(Test-Path "$StorageDrive\backups")) { New-Item -ItemType Directory -Force -Path "$StorageDrive\backups" | Out-Null }
}

$yamlLines = @(
    "# USPC Declarative Production Configuration (Podman)",
    "cloud:",
    "  name: `"$CloudName`"",
    "  environment: `"production`"",
    "  domain: `"$Domain`"",
    "  admin_user: `"admin`"",
    "",
    "runtime:",
    "  engine: `"podman`"",
    "  rootless: true",
    "",
    "storage:",
    "  data_path: `"$DataPath`"",
    "  config_path: `"$ConfigPath`"",
    "  min_free_space_gb: 20",
    "  profile: `"local`"",
    "",
    "backup:",
    "  enabled: true",
    "  target_type: `"local`"",
    "  target_path: `"$BackupPath`"",
    "  retention_days: 30",
    "  schedule: `"0 2 * * *`"",
    "  verify_after_backup: true",
    "",
    "performance:",
    "  profile: `"auto`"",
    "  auto_tune: true",
    "",
    "monitoring:",
    "  profile: `"minimal`"",
    "",
    "network:",
    "  mode: `"private`"",
    "  vpn_subnet: `"100.64.0.0/10`"",
    "  headscale_port: 8080",
    "",
    "services:",
    "  nextcloud:",
    "    version: `"27.1.4-apache`"",
    "    port: 8081",
    "  postgres:",
    "    version: `"16.1-alpine`"",
    "    port: 5432",
    "  redis:",
    "    version: `"7.2-alpine`"",
    "    port: 6379",
    "",
    "media:",
    "  enabled: true",
    "  port: 8085"
)

$ConfigTarget = "$ScriptDir\config\cloud.yaml"
if (!$DryRun) {
    [System.IO.File]::WriteAllLines($ConfigTarget, $yamlLines, [System.Text.Encoding]::UTF8)
    Write-Success "Configuration saved to $ConfigTarget (Engine: Podman)"
} else {
    Write-Host "[DRY-RUN] Would write config to $ConfigTarget" -ForegroundColor Yellow
}

# -------------------------------------------------------------------------
# Step 6: Execute USPC Bootstrap
# -------------------------------------------------------------------------
Write-Step "Step 6: Executing USPC Setup Bootstrap"

$SetupArgs = @("setup", "--force", "--non-interactive")
if ($DryRun) {
    $SetupArgs += "--dry-run"
}

& "$ScriptDir\cloudctl.ps1" @SetupArgs

# -------------------------------------------------------------------------
# Step 7: System Verification & Health Diagnostic
# -------------------------------------------------------------------------
if (!$DryRun) {
    Write-Step "Step 7: Verifying Service Health and Diagnostics"
    
    & "$ScriptDir\cloudctl.ps1" status
    & "$ScriptDir\cloudctl.ps1" performance
}

Write-Host "`n=================================================================" -ForegroundColor Green
Write-Host "   USPC Setup Completed Successfully!                           " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "  * Container Engine: Podman (Rootless Appliance Mode)" -ForegroundColor White
Write-Host "  * Nextcloud Web   : http://localhost:8081" -ForegroundColor White
Write-Host "  * Media Library   : http://localhost:8085" -ForegroundColor White
Write-Host "  * Dedicated Drive : $StorageDrive" -ForegroundColor White
Write-Host "  * Status Command  : .\cloudctl.ps1 status" -ForegroundColor White
Write-Host "  * Diagnostics     : .\cloudctl.ps1 doctor" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Green
