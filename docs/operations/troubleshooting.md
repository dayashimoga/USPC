# USPC Troubleshooting & Diagnostic Guide

When encountering issues with service startup, streaming, or networking, USPC provides built-in automated diagnostics.

## 1. Running System Diagnostics

```bash
./cloudctl doctor
```

To attempt automatic remediation of identified issues (such as restarting stopped containers):

```bash
./cloudctl doctor --fix
```

---

## 2. Inspecting Service Logs

Stream logs for any specific service:

```bash
./cloudctl logs -s nextcloud
./cloudctl logs -s media
./cloudctl logs -s postgres
./cloudctl logs -s redis
./cloudctl logs -s headscale
```

---

## 3. Common Issues & Solutions

### A. Port Conflict Detected on Startup

- **Symptom**: `Port collision: Port 8081 used by both ...`
- **Fix**: Open `config/cloud.yaml` and assign a unique port for the conflicting service under the `services` or `media` sections.

### B. High CPU / Throttled Transcoding

- **Symptom**: `[!] High CPU utilization (> 85%)` in `./cloudctl performance`
- **Fix**: Switch to a lighter resource profile:
  ```yaml
  performance:
    profile: "small" # or tiny
  ```

### C. Low Disk Space Warning

- **Symptom**: `Insufficient disk space at '~/.uspc/data'`
- **Fix**: Free up space on the host disk or migrate data to an external drive using:
  ```python
  # In config/cloud.yaml
  storage:
    data_path: "/mnt/external-drive/uspc-data"
  ```
