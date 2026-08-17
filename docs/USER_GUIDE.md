# USPC User Guide

> Getting started with your Universal Personal Cloud

## First Launch

### 1. Clone & Setup
```bash
git clone https://github.com/dayashimoga/USPC.git
cd USPC

# Install Python dependencies
pip install -e ".[dev]"

# One-command setup (or --dry-run to preview)
cloudctl setup --non-interactive
```

### 2. Verify Installation
```bash
cloudctl status          # Check service health
cloudctl doctor          # Run diagnostics
cloudctl readiness       # Production readiness check
```

### 3. Access Your Cloud
- **Nextcloud**: `http://localhost:8081` (or via VPN at your cloud domain)
- **Media Library**: `http://localhost:8085` (web interface)

---

## Authentication

USPC uses HMAC-SHA256 tokens for media service access. Tokens are:
- **Time-limited**: Expire after 24 hours by default.
- **Cryptographically signed**: Bound to user ID and item ID.
- **Revocable**: Can be revoked before expiry.

Nextcloud has its own authentication (admin password generated during setup, stored in secret vault).

---

## Media Library

### Browsing
Open `http://localhost:8085` in your browser. The SPA provides:
- **Grid view**: Thumbnail gallery of all media.
- **List view**: Sortable table with metadata.
- **Search**: Filter by filename, type, or metadata.

### Uploading Files
Upload via the web interface or API:
```bash
# API upload (requires authentication)
curl -X POST http://localhost:8085/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@video.mp4"
```

### Streaming
- **Video**: Click any video thumbnail → modal player with seeking, playback speed, volume.
- **Audio**: Click audio file → persistent bottom dock player with playlist.
- **Images**: Click image → lightbox viewer with zoom.

All streaming uses HTTP 206 Partial Content for instant seeking without downloading the entire file.

### Supported Formats

| Type | Formats |
|---|---|
| Video | MP4, WebM, MOV, MKV, AVI, WMV, FLV |
| Audio | MP3, AAC, M4A, FLAC, OGG, Opus, WAV, WMA |
| Image | JPG, JPEG, PNG, WebP, GIF, BMP, SVG, TIFF |

---

## Monitoring & Alerts

```bash
# Live dashboard
cloudctl monitor

# Check alerts
cloudctl alerts

# View service logs
cloudctl logs
cloudctl logs --service media --tail 50 --follow
```

---

## Backups

```bash
# Create backup
cloudctl backup --verify

# List and restore
cloudctl restore --dry-run      # Preview
cloudctl restore                # Restore latest
```

---

## Common Workflows

### Upgrade USPC
```bash
cloudctl update --dry-run       # Preview changes
cloudctl update                 # Apply with automatic rollback
```

### Clean Caches
```bash
cloudctl cleanup --dry-run      # Preview
cloudctl cleanup                # Clean temp files
```

### Export/Import Configuration
```bash
cloudctl config export --output my-config.yaml
cloudctl config import --input my-config.yaml
```

### Migrate to New Machine
```bash
# On old machine
cloudctl migrate export --output uspc-migration.tar.gz

# On new machine
cloudctl migrate import --input uspc-migration.tar.gz
```

---

## Expected Errors & What They Mean

| Error | Cause | Action |
|---|---|---|
| "Authentication required" | Missing or expired token | Re-authenticate or generate new token |
| "Access forbidden: Path traversal" | Attempted directory escape | Normal security protection — use valid paths |
| "Rate limit exceeded" | Too many requests | Wait and retry (default: 600 RPM limit) |
| "Restic CLI not available" | Restic not installed | Install Restic for backup functionality |

---

## Cross-References

- [Setup Guides](setup/) | [Configuration](CONFIGURATION.md) | [CLI Reference](CLI-REFERENCE.md)
- [Troubleshooting](TROUBLESHOOTING.md) | [Media Formats](media/supported-formats.md)
