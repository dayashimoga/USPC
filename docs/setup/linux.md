# USPC Linux Installation & Setup Guide

USPC runs natively on any modern Linux distribution (Ubuntu 20.04+, Debian 11+, Fedora 38+, RHEL/Alma/Rocky 8+, Arch Linux) on `x86_64` and `aarch64` (Raspberry Pi 4/5, ARM servers).

## Prerequisites

1. **Python 3.10+**: `sudo apt install python3 python3-pip python3-venv` (Debian/Ubuntu) or `sudo dnf install python3 python3-pip` (Fedora/RHEL).
2. **Podman (Recommended)**: `sudo apt install podman` or `sudo dnf install podman`.
3. **WireGuard (for client access)**: Included in Linux kernel 5.6+.

---

## One-Command Setup

```bash
# 1. Clone the repository
git clone https://github.com/dayashimoga/USPC.git
cd uspc


# 2. Complete one-command bootstrap (or add --dry-run to simulate)
./cloudctl setup

# Alternatively, step-by-step:
./cloudctl init
./cloudctl install
```

---

## Verification & Health Check

```bash
./cloudctl status
./cloudctl doctor
./cloudctl performance
./cloudctl security-check
```

---

## Accessing Your Cloud

- **Web Dashboard & Media Library**: `http://127.0.0.1:8085`
- **Nextcloud Web UI**: `http://127.0.0.1:8081`
- **Headscale VPN Control**: `http://127.0.0.1:8080`
