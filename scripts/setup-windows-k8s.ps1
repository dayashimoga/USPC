# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes / K3s Up Automation)
# Automated Provisioning for Windows (Minikube / K3d / Docker Desktop K8s / K3s)
# ==============================================================================

[CmdletBinding()]
param (
    [string]$StorageDrive = "D:\MyCloud",
    [string]$Namespace = "uspc",
    [switch]$PortForward = $true,
    [switch]$SkipWait = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "   USPC - Universal Personal Cloud Platform (Kubernetes Cluster) " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# Step 1: Detect kubectl and Cluster Connectivity
# -----------------------------------------------------------------------------
Write-Host "`n==> Step 1: Checking Kubernetes Prerequisites" -ForegroundColor Yellow

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "  [!] kubectl not found on PATH. Attempting automatic installation via winget..." -ForegroundColor Cyan
    try {
        winget install -e --id Kubernetes.kubectl --accept-package-agreements --accept-source-agreements --silent
        $env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:Path"
    } catch {
        Write-Warning "Could not auto-install kubectl. Please install kubectl or enable Kubernetes in Docker Desktop."
    }
}

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Error "kubectl is required. Please install kubectl (winget install Kubernetes.kubectl)."
}

Write-Host "  [OK] kubectl detected: $(kubectl version --client --short 2>$null | Select-Object -First 1)" -ForegroundColor Green

# Check if Kubernetes cluster is accessible
$null = kubectl cluster-info --request-timeout=2s 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [!] No active Kubernetes cluster responding. Checking for minikube or k3d..." -ForegroundColor Yellow
    if (Get-Command minikube -ErrorAction SilentlyContinue) {
        Write-Host "  [>] Starting Minikube cluster..." -ForegroundColor Cyan
        minikube start --driver=docker
    } elseif (Get-Command k3d -ErrorAction SilentlyContinue) {
        Write-Host "  [>] Creating k3d cluster 'uspc-cluster'..." -ForegroundColor Cyan
        k3d cluster create uspc-cluster --port "8081:80@loadbalancer" --port "8085:8085@loadbalancer"
    } else {
        Write-Host "  [!] Attempting to start Minikube via winget..." -ForegroundColor Cyan
        try {
            winget install -e --id Kubernetes.minikube --accept-package-agreements --accept-source-agreements --silent
            $env:Path = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:Path"
            minikube start --driver=docker
        } catch {
            Write-Warning "Could not start a local cluster. Ensure Docker Desktop Kubernetes, Minikube, or K3d is running."
        }
    }
}

# -----------------------------------------------------------------------------
# Step 2: Ensure Namespace and Secrets Exist
# -----------------------------------------------------------------------------
Write-Host "`n==> Step 2: Configuring Kubernetes Namespace & Secrets" -ForegroundColor Yellow

# Create namespace if missing
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
Write-Host "  [OK] Namespace '$Namespace' active." -ForegroundColor Green

# Generate / Load Secrets
$SecretsPath = "$HOME\.uspc\secrets\secrets.json"
$PgPass = "uspc_pg_pass_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 16)
$NcAdminPass = "uspc_admin_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 16)
$GrafanaPass = "uspc_grafana_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 16)
$MediaSecret = [System.Guid]::NewGuid().ToString("N") + [System.Guid]::NewGuid().ToString("N")

if (Test-Path $SecretsPath) {
    try {
        $sec = Get-Content $SecretsPath | ConvertFrom-Json
        if ($sec.postgres_password) { $PgPass = $sec.postgres_password }
        if ($sec.nextcloud_admin_password) { $NcAdminPass = $sec.nextcloud_admin_password }
        if ($sec.media_jwt_secret) { $MediaSecret = $sec.media_jwt_secret }
    } catch {}
}

kubectl create secret generic uspc-secrets -n $Namespace `
    --from-literal=postgres_password="$PgPass" `
    --from-literal=nextcloud_admin_password="$NcAdminPass" `
    --from-literal=grafana_password="$GrafanaPass" `
    --from-literal=media_jwt_secret="$MediaSecret" `
    --dry-run=client -o yaml | kubectl apply -f - | Out-Null

Write-Host "  [OK] Kubernetes secret 'uspc-secrets' synchronized." -ForegroundColor Green

# -----------------------------------------------------------------------------
# Step 3: Apply Declarative Kubernetes Manifests
# -----------------------------------------------------------------------------
Write-Host "`n==> Step 3: Applying Kustomize Manifests (deploy/k3s/)" -ForegroundColor Yellow

$ManifestDir = Join-Path $RepoRoot "deploy\k3s"
kubectl apply -k $ManifestDir -n $Namespace

Write-Host "  [OK] Kubernetes workloads and services submitted to cluster." -ForegroundColor Green

# -----------------------------------------------------------------------------
# Step 4: Await Pod Rollout Status
# -----------------------------------------------------------------------------
if (-not $SkipWait) {
    Write-Host "`n==> Step 4: Awaiting Pod Deployments Ready Status" -ForegroundColor Yellow
    $Deployments = @("postgres", "redis", "uspc-media", "nextcloud")
    foreach ($dep in $Deployments) {
        Write-Host "  [>] Rollout status for $dep..." -NoNewline
        try {
            kubectl rollout status deployment/$dep -n $Namespace --timeout=90s 2>$null | Out-Null
            Write-Host " [READY]" -ForegroundColor Green
        } catch {
            Write-Host " [IN PROGRESS / STARTING]" -ForegroundColor Yellow
        }
    }
}

# -----------------------------------------------------------------------------
# Step 5: Port Forwarding for Localhost Access
# -----------------------------------------------------------------------------
if ($PortForward) {
    Write-Host "`n==> Step 5: Setting Up Localhost Port Forwarding" -ForegroundColor Yellow
    
    # Kill any existing background port-forwards
    Get-Process -Name "kubectl" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "port-forward" } | Stop-Process -Force -ErrorAction SilentlyContinue

    # Start Port Forwarding Jobs
    Start-Process -FilePath "kubectl" -ArgumentList "port-forward -n $Namespace svc/nextcloud 8081:8081" -WindowStyle Hidden
    Start-Process -FilePath "kubectl" -ArgumentList "port-forward -n $Namespace svc/uspc-media 8085:8085" -WindowStyle Hidden
    Start-Process -FilePath "kubectl" -ArgumentList "port-forward -n $Namespace svc/uspc-grafana 3000:3000" -WindowStyle Hidden -ErrorAction SilentlyContinue

    Write-Host "  [OK] Forwarded Nextcloud       -> http://localhost:8081" -ForegroundColor Green
    Write-Host "  [OK] Forwarded USPC Media      -> http://localhost:8085" -ForegroundColor Green
    Write-Host "  [OK] Forwarded Grafana Metrics -> http://localhost:3000" -ForegroundColor Green
}

# -----------------------------------------------------------------------------
# Summary Dashboard
# -----------------------------------------------------------------------------
Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "   USPC Kubernetes Deployment is Live! " -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  * Nextcloud Cloud Storage : http://localhost:8081" -ForegroundColor White
Write-Host "  * USPC Media Library      : http://localhost:8085" -ForegroundColor White
Write-Host "  * Grafana Dashboard       : http://localhost:3000" -ForegroundColor White
Write-Host "  * Admin Username          : admin (or testadmin)" -ForegroundColor White
Write-Host "  * Kubernetes Namespace    : $Namespace" -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  To view pods:    kubectl get pods -n $Namespace" -ForegroundColor Gray
Write-Host "  To view logs:    kubectl logs -n $Namespace deployment/uspc-media" -ForegroundColor Gray
Write-Host "  To tear down:    .\scripts\k8s-down.ps1" -ForegroundColor Gray
Write-Host "=================================================================`n" -ForegroundColor Cyan
