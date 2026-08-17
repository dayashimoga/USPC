#!/usr/bin/env bash
# USPC Deployment Post-Flight Validation
set -euo pipefail

echo "==> Running USPC post-flight validation..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

python3 -m cloudctl doctor
python3 -m cloudctl security-check
