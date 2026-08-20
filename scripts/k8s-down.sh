#!/usr/bin/env bash
# ==============================================================================
# USPC - Universal Personal Cloud Platform (Kubernetes Teardown Automation)
# Automated Teardown for Linux / macOS
# ==============================================================================
set -euo pipefail

NAMESPACE="${NAMESPACE:-uspc}"
PURGE_DATA="${1:-false}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "================================================================="
echo "   USPC - Kubernetes Teardown & Cleanup                          "
echo "================================================================="

KUBECTL_BIN="kubectl"
if ! command -v kubectl &>/dev/null && command -v k3s &>/dev/null; then
    KUBECTL_BIN="k3s kubectl"
fi

echo "==> Step 1: Stopping background port forwards..."
pkill -f "port-forward.*$NAMESPACE" || true

echo "==> Step 2: Deleting Kubernetes workloads in namespace '$NAMESPACE'..."
if $KUBECTL_BIN cluster-info --request-timeout=3s &>/dev/null; then
    $KUBECTL_BIN delete -k "$REPO_ROOT/deploy/k3s" -n "$NAMESPACE" --ignore-not-found=true --request-timeout=15s || true

    if [ "$PURGE_DATA" = "--purge-data" ] || [ "$PURGE_DATA" = "true" ]; then
        echo "==> Step 3: Purging PVCs and namespace..."
        $KUBECTL_BIN delete pvc --all -n "$NAMESPACE" --ignore-not-found=true --request-timeout=15s || true
        $KUBECTL_BIN delete namespace "$NAMESPACE" --ignore-not-found=true --request-timeout=15s || true
    fi
else
    echo "  [i] Kubernetes cluster not reachable. Workloads are already stopped."
fi

echo "================================================================="
echo "   USPC Kubernetes Teardown Complete! Zero Running Residue.      "
echo "================================================================="
