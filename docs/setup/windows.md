# USPC Windows 10/11 Installation & Setup Guide

USPC runs on Windows 10/11 using WSL2 (Windows Subsystem for Linux), Podman Machine, or Docker Desktop.

## Prerequisites

1. **Python 3.10+**: Download from python.org or install via `winget install Python.Python.3.11`.
2. **WSL2 or Docker Engine**: `wsl --install` or install Docker Desktop / Podman.
3. **PowerShell 5.1+ or PowerShell 7+**.

---

## One-Command Setup

Open PowerShell:

```powershell
# 1. Clone repository
git clone https://github.com/dayashimoga/USPC.git
cd uspc


# 2. Run automated bootstrap (or add -DryRun to simulate)
.\cloudctl.ps1 setup

# Alternatively, step-by-step:
.\cloudctl.ps1 init
.\cloudctl.ps1 install
```

---

## Management Commands

```powershell
.\cloudctl.ps1 status        # View health dashboard
.\cloudctl.ps1 performance   # Live CPU/RAM/Disk metrics
.\cloudctl.ps1 benchmark     # Measure disk IO and stream throughput
.\cloudctl.ps1 backup        # Run encrypted snapshot backup
.\cloudctl.ps1 doctor        # Run diagnostics
```
