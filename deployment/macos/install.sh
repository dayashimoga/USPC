#!/usr/bin/env bash
# macOS deployment script for USPC (Podman Machine / Lima / Docker)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

echo "==> USPC macOS Setup"

python3 -m cloudctl init
python3 -m cloudctl install "$@"
