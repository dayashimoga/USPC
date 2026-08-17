#!/usr/bin/env bash
# Linux native deployment script for USPC
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

echo "==> USPC Linux Native Setup"

# Check rootless Podman
if command -v podman >/dev/null 2>&1; then
    echo "[+] Podman is available"
elif command -v docker >/dev/null 2>&1; then
    echo "[+] Docker is available"
fi

python3 -m cloudctl init
python3 -m cloudctl install "$@"
