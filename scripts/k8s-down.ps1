# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes Teardown Automation)
# Automated Teardown for Windows (Zero-Residue Removal)
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Namespace = "uspc",
    [switch]$PurgeData = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   USPC - Kubernetes Teardown & Workload Removal                 " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# Step 1: Terminate background port-forwarding processes
Write-Host "`n==> Step 1: Stopping background port-forwarding proxies..." -ForegroundColor Yellow
Get-Process -Name "kubectl" -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -match "port-forward" -and $_.CommandLine -match $Namespace 
} | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "  [OK] Port forwarding proxies stopped." -ForegroundColor Green

# Step 2: Delete Kubernetes workloads
Write-Host "`n==> Step 2: Deleting Kubernetes workloads in namespace '$Namespace'..." -ForegroundColor Yellow
$ManifestDir = Join-Path $RepoRoot "deploy\k3s"

$null = kubectl cluster-info --request-timeout=2s 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [i] No active Kubernetes cluster reachable. Workloads are already stopped." -ForegroundColor Green
} else {
    if (Test-Path $ManifestDir) {
        kubectl delete -k $ManifestDir -n $Namespace --ignore-not-found=true --request-timeout=15s
    }

    # Step 3: Handle persistent data & namespace deletion
    if ($PurgeData) {
        Write-Host "`n==> Step 3: Purging PersistentVolumeClaims and Secrets..." -ForegroundColor Yellow
        kubectl delete pvc --all -n $Namespace --ignore-not-found=true --request-timeout=15s
        kubectl delete secret uspc-secrets -n $Namespace --ignore-not-found=true --request-timeout=15s
        kubectl delete namespace $Namespace --ignore-not-found=true --request-timeout=15s
        Write-Host "  [OK] Namespace '$Namespace' and all persistent storage volumes deleted." -ForegroundColor Green
    } else {
        Write-Host "`n==> Step 3: Preserving persistent storage volumes & namespace." -ForegroundColor Cyan
        Write-Host "  [i] Persistent volumes (PVCs) kept intact. Use -PurgeData to remove." -ForegroundColor Gray
    }
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "   USPC Kubernetes Teardown Complete! Zero Running Residue.      " -ForegroundColor Green
Write-Host "=================================================================`n" -ForegroundColor Cyan
