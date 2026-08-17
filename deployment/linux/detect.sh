#!/usr/bin/env bash
# Linux environment inspection helper
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

python3 -c "from cloudctl.core.detect import detect_host; import json; print(json.dumps(detect_host().to_dict(), indent=2))"
