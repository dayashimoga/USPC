# USPC macOS Installation & Setup Guide

USPC runs on macOS 12+ (Monterey, Ventura, Sonoma, Sequoia) on both Apple Silicon (M1/M2/M3/M4) and Intel Macs using Podman Machine or Docker.

## Prerequisites

1. **Python 3.10+**: `brew install python`
2. **Podman (Recommended)**: `brew install podman`
   ```bash
   podman machine init --cpus 4 --memory 4096
   podman machine start
   ```

---

## One-Command Setup

```bash
# 1. Clone repository
git clone https://github.com/dayashimoga/USPC.git
cd uspc


# 2. Run automated bootstrap (or add --dry-run to simulate)
./cloudctl setup

# Alternatively, step-by-step:
./cloudctl init
./cloudctl install
```

---

## Accessing Services

- **Web Dashboard**: `http://localhost:8085`
- **Nextcloud Web UI**: `http://localhost:8081`
- **Status Dashboard**: `./cloudctl status`
- **Performance Monitor**: `./cloudctl performance`
