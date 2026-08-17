"""Tests for security headers middleware, Prometheus /metrics endpoint, and environment profiles."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from cloudctl.core.config import ConfigManager
from media.app import create_app
from media.config import MediaConfig


def test_api_security_headers_and_metrics_endpoint(temp_dir: Path):
    cfg = MediaConfig(
        data_path=temp_dir / "data",
        cache_path=temp_dir / "cache",
        background_processing=False,
    )

    app = create_app(cfg)
    client = TestClient(app)

    # Check health response headers
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert res.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "X-Process-Time-Ms" in res.headers

    # Check Prometheus /metrics endpoint
    res_m = client.get("/metrics")
    assert res_m.status_code == 200
    assert "text/plain" in res_m.headers.get("content-type", "")
    assert "uspc_cpu_utilization_percent" in res_m.text
    assert "uspc_active_streams" in res_m.text
    assert "uspc_library_total_items" in res_m.text


def test_environment_profile_resolution(temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_mgr = ConfigManager(config_path=cfg_file)

    # Dev profile
    dev_cfg = cfg_mgr.get_effective_config(profile="dev")
    assert dev_cfg["cloud"]["environment"] == "development"
    assert dev_cfg["performance"]["rate_limit_requests_per_minute"] == 10000

    # Cluster profile
    cluster_cfg = cfg_mgr.get_effective_config(profile="cluster")
    assert cluster_cfg["orchestrator"]["mode"] == "cluster"

    # Appliance profile
    appliance_cfg = cfg_mgr.get_effective_config(profile="appliance")
    assert appliance_cfg["orchestrator"]["mode"] == "appliance"


def test_audit_log_auth_event_execution():
    from media.auth import audit_log_auth_event

    # Should execute without error
    audit_log_auth_event("LOGIN", "admin", "127.0.0.1", "item-1", True, "successful login")
    audit_log_auth_event("STREAM", "user", "10.0.0.1", "item-2", False, "expired token")

