"""Unit tests for production acceptance gap closure, hardware probing, alert lifecycle, and SBOM drift."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from cloudctl.commands.acceptance import execute_acceptance, execute_hardware_acceptance
from cloudctl.commands.alerts import execute_alerts_cmd, simulate_alert_lifecycle
from cloudctl.commands.sbom_cmd import execute_sbom_cmd, verify_sbom_drift
from cloudctl.core.network import NetworkManager


def test_hardware_acceptance_workflow(temp_dir: Path, mock_config_dict: dict):
    cfg_file = temp_dir / "cloud.yaml"
    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # 1. Without endpoint (PENDING status)
    args = argparse.Namespace(
        config=str(cfg_file),
        hardware=True,
        endpoint=None,
        json=False,
    )
    rc = execute_acceptance(args)
    assert rc == 0

    # 2. JSON output mode
    args_json = argparse.Namespace(
        config=str(cfg_file),
        hardware=True,
        endpoint=None,
        json=True,
    )
    rc_json = execute_hardware_acceptance(args_json)
    assert rc_json == 0


def test_probe_hardware_wan_with_mocked_socket(temp_dir: Path, mock_config_dict: dict):
    nm = NetworkManager(mock_config_dict, config_dir=temp_dir)

    # Success case with endpoint
    with patch("socket.create_connection", return_value=MagicMock()):
        res = nm.probe_hardware_wan(target_endpoint="10.0.0.1:8080")
        assert res["status"] == "PASS"
        assert res["classification"] == "HARDWARE-PROVEN"
        assert res["endpoint_reachable"] is True

    # Failure case with endpoint
    with patch("socket.create_connection", side_effect=OSError("Connection refused")):
        res_fail = nm.probe_hardware_wan(target_endpoint="10.0.0.1:8080")
        assert res_fail["status"] == "FAIL"
        assert res_fail["endpoint_reachable"] is False


def test_alert_lifecycle_and_cli_actions():
    cycle = simulate_alert_lifecycle()
    assert len(cycle) == 4
    assert cycle[0]["status"] == "TRIGGERED"
    assert cycle[1]["status"] == "FIRING"
    assert cycle[2]["status"] == "ACKNOWLEDGED"
    assert cycle[3]["status"] == "RESOLVED"

    # Test simulate-cycle CLI
    args_sim = argparse.Namespace(
        profile="minimal",
        simulate_cycle=True,
        acknowledge=None,
        resolve=None,
        fail_on_critical=False,
        json=False,
    )
    assert execute_alerts_cmd(args_sim) == 0

    # Test acknowledge and resolve CLI
    args_ack = argparse.Namespace(
        profile="minimal",
        simulate_cycle=False,
        acknowledge="ALT-1001",
        resolve=None,
        fail_on_critical=False,
        json=False,
    )
    assert execute_alerts_cmd(args_ack) == 0

    args_res = argparse.Namespace(
        profile="minimal",
        simulate_cycle=False,
        acknowledge=None,
        resolve="ALT-1001",
        fail_on_critical=False,
        json=False,
    )
    assert execute_alerts_cmd(args_res) == 0


def test_sbom_drift_verification_and_cli(temp_dir: Path):
    clean, drift = verify_sbom_drift()
    assert clean is True
    assert len(drift) == 0

    args_drift = argparse.Namespace(
        verify_drift=True,
        audit=False,
        format="text",
        output=None,
        json=False,
    )
    assert execute_sbom_cmd(args_drift) == 0

    # Drift failure branch
    with patch(
        "cloudctl.commands.sbom_cmd.OPEN_SOURCE_DEPENDENCIES",
        [{"name": "fake", "version": None, "license": "MIT"}],
    ):
        drift_clean, drift_items = verify_sbom_drift()
        assert drift_clean is False
        assert len(drift_items) > 0
        assert execute_sbom_cmd(args_drift) == 1

    # License audit failure branch
    args_audit = argparse.Namespace(
        verify_drift=False,
        audit=True,
        format="text",
        output=None,
        json=False,
    )
    with patch(
        "cloudctl.commands.sbom_cmd.OPEN_SOURCE_DEPENDENCIES",
        [
            {
                "name": "fake_saas",
                "version": "1.0",
                "license": "Proprietary Commercial",
                "purpose": "lockin",
            }
        ],
    ):
        assert execute_sbom_cmd(args_audit) == 1

    # CycloneDX export to file
    out_cdx = temp_dir / "sbom.cdx.json"
    args_cdx = argparse.Namespace(
        verify_drift=False,
        audit=False,
        format="cyclonedx",
        output=str(out_cdx),
        json=False,
    )
    assert execute_sbom_cmd(args_cdx) == 0
    assert out_cdx.exists()

    # SPDX JSON export to file
    out_spdx = temp_dir / "sbom.spdx.json"
    args_spdx = argparse.Namespace(
        verify_drift=False,
        audit=False,
        format="json",
        output=str(out_spdx),
        json=True,
    )
    assert execute_sbom_cmd(args_spdx) == 0
    assert out_spdx.exists()


def test_alertmanager_manifest_syntax():
    manifest_path = Path("deploy/k3s/11-monitoring-alertmanager.yaml")
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")
    docs = list(yaml.safe_load_all(content))
    assert len(docs) == 3  # ConfigMap, Deployment, Service
    kinds = [d["kind"] for d in docs]
    assert "ConfigMap" in kinds
    assert "Deployment" in kinds
    assert "Service" in kinds


def test_generate_production_gap_matrix():
    from cloudctl.commands.acceptance import generate_production_gap_matrix

    gap_data = generate_production_gap_matrix()
    assert gap_data["total_areas"] == 15
    assert gap_data["unresolved_software_gaps"] == 0
    assert gap_data["hardware_dependent_gates"] == 1
    assert len(gap_data["gap_matrix"]) == 15

    for item in gap_data["gap_matrix"]:
        assert "area" in item
        assert "requirement" in item
        assert "implementation" in item
        assert "evidence_class" in item
        assert "status" in item


def test_acceptance_strict_mode_and_multi_reports(temp_dir: Path, mock_config_dict: dict):
    from cloudctl.commands.acceptance import generate_acceptance_report

    cfg_file = temp_dir / "cloud.yaml"
    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")
    out_dir = temp_dir / "reports"

    # Test report exports with strict=False
    args = argparse.Namespace(
        config=str(cfg_file),
        full=False,
        hardware=False,
        strict=False,
        json=False,
        output_dir=str(out_dir),
    )
    assert execute_acceptance(args) in (0, 1)
    assert (out_dir / "acceptance.json").exists()

    assert (out_dir / "acceptance.html").exists()
    assert (out_dir / "production-readiness.json").exists()
    assert (out_dir / "production-readiness.html").exists()
    assert (out_dir / "gap-matrix.json").exists()
    assert (out_dir / "test-summary.json").exists()
    assert (out_dir / "performance.json").exists()
    assert (out_dir / "resilience.json").exists()
    assert (out_dir / "dr-rpo-rto.json").exists()
    assert (out_dir / "upgrade-rollback.json").exists()
    assert (out_dir / "monitoring.json").exists()
    assert (out_dir / "security.json").exists()
    assert (out_dir / "SBOM.spdx.json").exists()
    assert (out_dir / "SBOM.cyclonedx.json").exists()
    assert (out_dir / "production-gap-audit.json").exists()

    # Test strict success when status is ACCEPTED
    rep_ok = generate_acceptance_report(config_path=str(cfg_file))
    rep_ok.overall_status = "ACCEPTED"
    with patch("cloudctl.commands.acceptance.generate_acceptance_report", return_value=rep_ok):
        args_strict_pass = argparse.Namespace(
            config=str(cfg_file),
            full=False,
            hardware=False,
            strict=True,
            json=False,
            output_dir=None,
        )
        assert execute_acceptance(args_strict_pass) == 0

    # Test strict failure when status is REJECTED
    rep_fail = generate_acceptance_report(config_path=str(cfg_file))
    rep_fail.overall_status = "REJECTED"
    with patch("cloudctl.commands.acceptance.generate_acceptance_report", return_value=rep_fail):
        args_strict_fail = argparse.Namespace(
            config=str(cfg_file),
            full=False,
            hardware=False,
            strict=True,
            json=False,
            output_dir=None,
        )
        assert execute_acceptance(args_strict_fail) == 1

        args_json_fail = argparse.Namespace(
            config=str(cfg_file),
            full=False,
            hardware=False,
            strict=True,
            json=True,
            output_dir=None,
        )
        assert execute_acceptance(args_json_fail) == 1
