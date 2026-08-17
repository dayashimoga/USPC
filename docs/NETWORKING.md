# USPC Networking

> Module: `src/cloudctl/core/network.py`

## Network Modes

| Mode | Config | Behavior |
|---|---|---|
| `private` (default) | `network.mode: "private"` | All services accessible only via WireGuard VPN. No public ports. |
| `public` | `network.mode: "public"` | HTTP/HTTPS ports exposed. Requires TLS configuration. |

---

## Headscale / WireGuard VPN

USPC uses self-hosted [Headscale](https://github.com/juanfont/headscale) as the control server for WireGuard mesh networking.

**How it works**:
1. `cloudctl setup` generates Headscale configuration (`~/.uspc/config/headscale/config.yaml`).
2. Headscale runs as a container on port 8080 (configurable).
3. Client devices install WireGuard and connect via Headscale.
4. All USPC services are accessible through the VPN tunnel.

**Configuration generated** (`NetworkManager.generate_headscale_config()`):
- Server URL, listen address, metrics endpoint
- VPN subnet (default: `100.64.0.0/10`)
- Private keys (from secret vault)
- MagicDNS configuration
- DERP relay servers

### Peer Enrollment
```bash
# On the USPC server (requires headscale CLI)
headscale nodes register --user <username> --key <node_key>

# Or via cloudctl
cloudctl acceptance --hardware --endpoint <peer-ip:port>
```

---

## Port Matrix

| Port | Service | Protocol | Access Level |
|---|---|---|---|
| 5432 | PostgreSQL | TCP | localhost-only |
| 6379 | Redis | TCP | localhost-only |
| 8080 | Headscale VPN Control | TCP | vpn-only (or public) |
| 8081 | Nextcloud Web | TCP | vpn-only |
| 8085 | USPC Media Service | TCP | vpn-only |
| 80 | HTTP Proxy | TCP | public (public mode only) |
| 443 | HTTPS Proxy | TCP | public (public mode only) |
| 9090 | Prometheus | TCP | localhost-only (cluster mode) |
| 3000 | Grafana | TCP | vpn-only (cluster mode) |
| 3100 | Loki | TCP | localhost-only (cluster mode) |

---

## Firewall Requirements

### Private Mode (default)
- **Inbound**: Allow port 8080/TCP (Headscale) from WAN if remote access needed.
- **Outbound**: Allow HTTPS (443) for DERP relay connections.
- **All other ports**: No inbound rules needed.

### Public Mode
- **Inbound**: Allow 80/TCP, 443/TCP, 8080/TCP.
- **Requirement**: TLS certificate must be configured (`security.tls_enabled: true`).

---

## K3s Cluster Networking

In cluster mode, K3s manages its own overlay network (Flannel VXLAN by default):
- Pod-to-pod communication via Flannel.
- Services exposed via K3s Ingress (`deploy/k3s/07-ingress.yaml`).
- Node-to-node communication requires open ports: 6443 (API), 8472/UDP (VXLAN), 10250 (kubelet).

---

## Physical WAN Verification

Multi-device WAN mesh routing across distinct ISPs requires physical hardware:

```bash
# Probe a remote physical peer
cloudctl acceptance --hardware --endpoint 192.168.1.50:8080

# Output includes:
# - Physical network adapter count
# - WireGuard adapter detection
# - Reachability verdict (PASS / PENDING / FAIL)
# - Round-trip latency (ms)
```

**Status**: `HARDWARE-PENDING` — cannot be validated without physical multi-device setup.

---

## Troubleshooting

| Symptom | Diagnosis | Fix |
|---|---|---|
| Cannot connect via VPN | Headscale not running | `cloudctl start`, check `cloudctl logs -s headscale` |
| Port 8080 unreachable | Firewall blocking | Open port 8080/TCP inbound |
| Peer not registered | Missing node key | Re-register peer via `headscale nodes register` |
| High latency | DERP relay in use | Check direct WireGuard connection |

---

## Cross-References

- [Architecture](ARCHITECTURE.md) | [Security](../SECURITY.md) | [Configuration](CONFIGURATION.md)
- [Setup Guides](setup/) | [Troubleshooting](TROUBLESHOOTING.md)
