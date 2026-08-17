#!/usr/bin/env bash
# USPC One-Command Safe Bootstrap Script
set -euo pipefail

echo "====================================================="
echo " Universal Personal Cloud Platform (USPC) Installer "
echo "====================================================="

# Clone repository if running standalone
if [ ! -f "pyproject.toml" ]; then
    echo "==> Cloning USPC repository..."
    git clone https://github.com/uspc-project/uspc.git
    cd uspc
fi

# Run cloudctl initialization
./cloudctl init
./cloudctl install "$@"
