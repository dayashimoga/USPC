#!/usr/bin/env bash
# USPC Offline Bundle Packager
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

python3 -m cloudctl bundle create --output "uspc-offline-bundle-$(date +%Y%m%d).tar.gz"
