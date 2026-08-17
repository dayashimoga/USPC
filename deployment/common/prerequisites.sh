#!/usr/bin/env bash
# USPC Shared Prerequisite Validator
set -euo pipefail

echo "==> Validating USPC prerequisites..."

# Check Python 3.10+
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "[+] Python 3 detected (v${PY_VER})"
else
    echo "[!] Python 3 is required. Please install Python 3.10+."
    exit 1
fi

# Check Container Engine
if command -v podman >/dev/null 2>&1; then
    echo "[+] Podman engine detected (Recommended)"
elif command -v docker >/dev/null 2>&1; then
    echo "[+] Docker engine detected"
else
    echo "[!] No container engine detected. Please install Podman or Docker."
    exit 1
fi

echo "==> Prerequisites check PASSED."
