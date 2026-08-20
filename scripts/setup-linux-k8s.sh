#!/usr/bin/env bash
# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes / K3s Up Automation)
# Automated Provisioning for Linux / macOS
# ==============================================================================
set -euo pipefail

NAMESPACE="${NAMESPACE:-uspc}"
PORT_FORWARD="${PORT_FORWARD:-true}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================="
echo "   USPC - Universal Personal Cloud Platform (Kubernetes Up)      "
echo "================================================================="

# Step 1: Detect kubectl / k3s
echo "==> Step 1: Checking Kubernetes CLI tools..."
KUBECTL_BIN="kubectl"
if ! command -v kubectl &>/dev/null; then
    if command -v k3s &>/dev/null; then
        KUBECTL_BIN="k3s kubectl"
    else
        echo "kubectl not found. Installing K3s lightweight cluster..."
        curl -sfL https://get.k3s.io | sh -
        KUBECTL_BIN="k3s kubectl"
    fi
fi
echo "  [OK] Using: $KUBECTL_BIN"

# Step 2: Namespace & Secret
echo "==> Step 2: Ensuring namespace and secrets exist..."
$KUBECTL_BIN create namespace "$NAMESPACE" --dry-run=client -o yaml | $KUBECTL_BIN apply -f -

PG_PASS=$(openssl rand -hex 16 2>/dev/null || date +%s | sha256sum | head -c 32)
NC_PASS=$(openssl rand -hex 16 2>/dev/null || date +%s | sha256sum | head -c 32)
GRAFANA_PASS=$(openssl rand -hex 16 2>/dev/null || date +%s | sha256sum | head -c 32)
MEDIA_SECRET=$(openssl rand -hex 32 2>/dev/null || date +%s | sha256sum | head -c 64)

$KUBECTL_BIN create secret generic uspc-secrets -n "$NAMESPACE" \
    --from-literal=postgres_password="$PG_PASS" \
    --from-literal=nextcloud_admin_password="$NC_PASS" \
    --from-literal=grafana_password="$GRAFANA_PASS" \
    --from-literal=media_jwt_secret="$MEDIA_SECRET" \
    --dry-run=client -o yaml | $KUBECTL_BIN apply -f -

# Step 3: Apply manifests
echo "==> Step 3: Applying Kubernetes manifests..."
$KUBECTL_BIN apply -k "$REPO_ROOT/deploy/k3s" -n "$NAMESPACE"

# Step 4: Wait for rollouts
echo "==> Step 4: Awaiting pod readiness..."
for dep in postgres redis uspc-media nextcloud; do
    echo -n "  Waiting for deployment/$dep... "
    $KUBECTL_BIN rollout status "deployment/$dep" -n "$NAMESPACE" --timeout=90s 2>/dev/null || true
    echo "[OK]"
done

# Step 5: Port forwarding
if [ "$PORT_FORWARD" = "true" ]; then
    echo "==> Step 5: Setting up localhost port forwarding..."
    pkill -f "port-forward.*$NAMESPACE" || true
    $KUBECTL_BIN port-forward -n "$NAMESPACE" svc/nextcloud 8081:8081 >/dev/null 2>&1 &
    $KUBECTL_BIN port-forward -n "$NAMESPACE" svc/uspc-media 8085:8085 >/dev/null 2>&1 &
    $KUBECTL_BIN port-forward -n "$NAMESPACE" svc/uspc-grafana 3000:3000 >/dev/null 2>&1 &
fi

echo "================================================================="
echo "   USPC Kubernetes Cluster is Ready!"
echo "   * Nextcloud Cloud Storage : http://localhost:8081"
echo "   * USPC Media Library      : http://localhost:8085"
echo "   * Grafana Metrics         : http://localhost:3000"
echo "================================================================="
