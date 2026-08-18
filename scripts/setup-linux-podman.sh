#!/usr/bin/env bash
# USPC Full Automation Setup Script for Linux (Rootless Podman + Dedicated Partition)
set -euo pipefail

STORAGE_MOUNT="${1:-/mnt/uspc_data}"
CLOUD_NAME="${2:-linux-cloud}"
DOMAIN="${3:-linux-cloud.local}"

echo "================================================================="
echo "   USPC — Universal Personal Cloud Platform (Linux + Podman)     "
echo "================================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

echo "==> Step 1: Checking & Installing Prerequisites (Podman, Python3, Git)"
if ! command -v podman &> /dev/null; then
    echo "Installing Podman..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y podman python3 python3-pip python3-venv git
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y podman python3 python3-pip git
    elif command -v pacman &> /dev/null; then
        sudo pacman -Sy --noconfirm podman python python-pip git
    fi
fi

echo "==> Step 2: Preparing Dedicated Storage Mount ($STORAGE_MOUNT)"
sudo mkdir -p "$STORAGE_MOUNT/data" "$STORAGE_MOUNT/config" "$STORAGE_MOUNT/backups"
sudo chown -R "$(id -u):$(id -g)" "$STORAGE_MOUNT"

echo "==> Step 3: Installing Python Dependencies"
cd "$SCRIPT_DIR"
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -e ".[dev]" --quiet

echo "==> Step 4: Generating Declarative Configuration (config/cloud.yaml)"
cat <<EOF > "${SCRIPT_DIR}/config/cloud.yaml"
# USPC Declarative Production Configuration (Linux Podman)
cloud:
  name: "${CLOUD_NAME}"
  environment: "production"
  domain: "${DOMAIN}"
  admin_user: "admin"

storage:
  data_path: "${STORAGE_MOUNT}/data"
  config_path: "${STORAGE_MOUNT}/config"
  min_free_space_gb: 20
  profile: "local"

backup:
  enabled: true
  target_type: "local"
  target_path: "${STORAGE_MOUNT}/backups"
  retention_days: 30
  schedule: "0 2 * * *"
  verify_after_backup: true

performance:
  profile: "auto"
  auto_tune: true

monitoring:
  profile: "minimal"

network:
  mode: "private"
  vpn_subnet: "100.64.0.0/10"
  headscale_port: 8080

services:
  nextcloud:
    version: "27.1.4-apache"
    port: 8081
  postgres:
    version: "16.1-alpine"
    port: 5432
  redis:
    version: "7.2-alpine"
    port: 6379

media:
  enabled: true
  port: 8085
EOF

echo "==> Step 5: Bootstrapping USPC System"
"${SCRIPT_DIR}/cloudctl" setup --non-interactive

echo "==> Step 6: Verifying Health"
"${SCRIPT_DIR}/cloudctl" status
"${SCRIPT_DIR}/cloudctl" performance

echo "================================================================="
echo "   USPC Setup Completed Successfully!                            "
echo "================================================================="
echo "  * Nextcloud Web   : http://localhost:8081"
echo "  * Media Library   : http://localhost:8085"
echo "  * Storage Mount   : $STORAGE_MOUNT"
echo "  * CLI Control     : ./cloudctl status"
echo "================================================================="
