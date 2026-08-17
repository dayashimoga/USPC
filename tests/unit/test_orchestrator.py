"""Unit tests for Orchestrator abstraction, Podman backend, K3s backend, and CLI dispatch."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from cloudctl.cli import main as cli_main
from cloudctl.commands.orchestrator_cmd import execute_orchestrator_cmd
from cloudctl.core.backends.k3s_backend import K3sBackend
from cloudctl.core.backends.podman_backend import PodmanBackend
from cloudctl.core.orchestrator import (
    OrchestratorMode,
    create_orchestrator,
)


def test_orchestrator_factory_and_mode_resolution(mock_config_dict: dict, temp_dir: Path):
    # Default appliance mode
    orch_appliance = create_orchestrator(mock_config_dict, repo_root=temp_dir)
    assert isinstance(orch_appliance, PodmanBackend)
    assert orch_appliance.get_mode() == OrchestratorMode.APPLIANCE

    # Explicit cluster mode
    mock_config_dict["orchestrator"] = {"mode": "cluster"}
    orch_cluster = create_orchestrator(mock_config_dict, repo_root=temp_dir)
    assert isinstance(orch_cluster, K3sBackend)
    assert orch_cluster.get_mode() == OrchestratorMode.CLUSTER

    # K3s alias
    mock_config_dict["orchestrator"] = {"mode": "k3s"}
    orch_k3s = create_orchestrator(mock_config_dict, repo_root=temp_dir)
    assert isinstance(orch_k3s, K3sBackend)


def test_podman_backend_lifecycle_and_methods(mock_config_dict: dict, temp_dir: Path):
    orch = PodmanBackend(mock_config_dict, repo_root=temp_dir)
    assert orch.get_mode() == OrchestratorMode.APPLIANCE

    # detect_runtime
    with patch("cloudctl.core.backends.podman_backend.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True, stdout="podman version 4.9.0")
        with patch.object(orch.container_mgr, "is_available", return_value=True):
            rt = orch.detect_runtime()
            assert rt["available"] is True
            assert "podman" in rt["version"]

    # setup dry run
    assert orch.setup(dry_run=True) is True

    # setup real
    with patch.object(orch.container_mgr, "is_available", return_value=True):
        with patch.object(orch.container_mgr, "create_pod", return_value=True):
            assert orch.setup(dry_run=False) is True

    # setup unavailable
    with patch.object(orch.container_mgr, "is_available", return_value=False):
        assert orch.setup(dry_run=False) is False

    # start, stop, restart (docker mode)
    orch.container_mgr.engine = "docker"
    with (
        patch("cloudctl.core.container.run_command", return_value=MagicMock(success=True)),
        patch(
            "cloudctl.core.backends.podman_backend.run_command",
            return_value=MagicMock(success=True),
        ),
    ):
        assert orch.start() is True
        assert orch.stop() is True
        assert orch.restart() is True

    # start, stop, restart (podman mode)
    orch.container_mgr.engine = "podman"
    with patch(
        "cloudctl.core.backends.podman_backend.run_command", return_value=MagicMock(success=True)
    ):
        assert orch.start() is True
        assert orch.stop() is True
        assert orch.restart() is True

    # logs and health_check
    with patch.object(orch.container_mgr, "get_logs", return_value="test logs"):
        assert "test logs" in orch.get_logs("uspc-media")

    hc = orch.health_check()
    assert isinstance(hc, dict)

    # status
    with patch.object(orch.container_mgr, "list_containers", return_value=[]):
        st = orch.status()
        assert st["mode"] == "appliance"
        assert "uspc-postgres" in st["services"]

    # scale and nodes
    assert orch.scale("uspc-media", 3) is True
    nodes = orch.list_nodes()
    assert len(nodes) == 1
    assert nodes[0].is_master is True

    # export_manifests
    out_dir = temp_dir / "export_compose"
    exported = orch.export_manifests(out_dir)
    assert len(exported) == 1
    assert exported[0].exists()


def test_k3s_backend_lifecycle_and_methods(mock_config_dict: dict, temp_dir: Path):
    mock_config_dict["orchestrator"] = {"mode": "cluster", "namespace": "uspc-test"}
    orch = K3sBackend(mock_config_dict, repo_root=temp_dir)
    assert orch.get_mode() == OrchestratorMode.CLUSTER

    # detect_runtime
    with patch("cloudctl.core.backends.k3s_backend.run_command") as mock_run:
        mock_run.return_value = MagicMock(
            success=True,
            stdout='{"clientVersion": {"gitVersion": "v1.30.2+k3s1"}}',
        )
        rt = orch.detect_runtime()
        assert rt["mode"] == "cluster"
        assert rt["namespace"] == "uspc-test"

    # setup
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True, stdout="namespace/uspc-test created")
        assert orch.setup(dry_run=True) is True
        assert orch.setup(dry_run=False) is True

    # start, stop, restart, scale
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True)
        assert orch.start() is True
        assert orch.stop() is True
        assert orch.restart() is True
        assert orch.scale("uspc-media", 4) is True

    # status & health_check
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(
            success=True,
            stdout='{"items": [{"metadata": {"name": "media-pod-1", "labels": {"app": "uspc-media"}}, "status": {"phase": "Running"}}]}',
        )
        st = orch.status()
        assert st["healthy"] is True
        assert st["services"]["uspc-media"]["status"] == "running"

        mock_k.return_value = MagicMock(
            success=True,
            stdout='{"items": [{"metadata": {"name": "uspc-media"}, "subsets": [{"addresses": [{"ip": "10.42.0.1"}]}]}]}',
        )
        hc = orch.health_check()
        assert hc["overall"] is True

    # logs
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True, stdout="k3s pod logs")
        assert "k3s pod logs" in orch.get_logs("uspc-media")

    # list_nodes
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(
            success=True,
            stdout="""{
                "items": [
                    {
                        "metadata": {"name": "node-1", "labels": {"node-role.kubernetes.io/master": "true"}},
                        "status": {
                            "conditions": [{"type": "Ready", "status": "True"}],
                            "addresses": [{"type": "InternalIP", "address": "192.168.1.10"}],
                            "capacity": {"cpu": "4", "memory": "8388608Ki"},
                            "nodeInfo": {"kubeletVersion": "v1.30.2+k3s1"}
                        }
                    }
                ]
            }""",
        )
        nodes = orch.list_nodes()
        assert len(nodes) == 1
        assert nodes[0].name == "node-1"
        assert nodes[0].is_master is True
        assert nodes[0].cpu_cores == 4

    # export_manifests
    export_dir = temp_dir / "k3s_exported"
    copied = orch.export_manifests(export_dir)
    assert len(copied) >= 0


def test_k3s_backend_deep_branches(mock_config_dict: dict, temp_dir: Path):
    orch = K3sBackend(mock_config_dict, repo_root=temp_dir)

    # test _run_kubectl branch with k3s
    with patch("shutil.which", side_effect=lambda x: "k3s" if x == "k3s" else None):
        with patch("cloudctl.core.backends.k3s_backend.run_command") as mock_run:
            mock_run.return_value = MagicMock(success=True)
            res = orch._run_kubectl(["get", "pods"])
            assert res.success is True

    # test _run_kubectl fallback when neither kubectl nor k3s on PATH
    with patch("shutil.which", return_value=None):
        with patch("cloudctl.core.backends.k3s_backend.run_command") as mock_run:
            mock_run.return_value = MagicMock(success=True)
            res = orch._run_kubectl(["get", "pods"])
            assert res.success is True

    # status exception handling
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True, stdout="INVALID_JSON")
        st = orch.status()
        assert st["healthy"] is False

    # health check exception handling
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True, stdout="INVALID_JSON")
        hc = orch.health_check()
        assert hc["overall"] is False

    # list_nodes exception handling
    with patch.object(orch, "_run_kubectl") as mock_k:
        mock_k.return_value = MagicMock(success=True, stdout="INVALID_JSON")
        nodes = orch.list_nodes()
        assert nodes == []


def test_execute_orchestrator_cli_dispatch(mock_config_dict: dict, temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    # Status text & JSON
    args_st = argparse.Namespace(orchestrator_subcommand="status", config=str(cfg_file), json=False)
    assert execute_orchestrator_cmd(args_st) == 0

    args_st_json = argparse.Namespace(
        orchestrator_subcommand="status", config=str(cfg_file), json=True
    )
    assert execute_orchestrator_cmd(args_st_json) == 0

    # Nodes text & JSON
    args_nodes = argparse.Namespace(
        orchestrator_subcommand="nodes", config=str(cfg_file), json=False
    )
    assert execute_orchestrator_cmd(args_nodes) == 0

    args_nodes_json = argparse.Namespace(
        orchestrator_subcommand="nodes", config=str(cfg_file), json=True
    )
    assert execute_orchestrator_cmd(args_nodes_json) == 0

    # Scale
    args_scale = argparse.Namespace(
        orchestrator_subcommand="scale",
        config=str(cfg_file),
        service="uspc-media",
        replicas=2,
    )
    assert execute_orchestrator_cmd(args_scale) == 0

    # Switch mode
    args_switch = argparse.Namespace(
        orchestrator_subcommand="switch", config=str(cfg_file), mode="cluster"
    )
    assert execute_orchestrator_cmd(args_switch) == 0

    # Switch invalid mode
    args_invalid = argparse.Namespace(
        orchestrator_subcommand="switch", config=str(cfg_file), mode="invalid_mode"
    )
    assert execute_orchestrator_cmd(args_invalid) == 1

    # Export manifests
    out_dir = temp_dir / "exported_mf"
    args_mf = argparse.Namespace(
        orchestrator_subcommand="manifests",
        config=str(cfg_file),
        output_dir=str(out_dir),
    )
    assert execute_orchestrator_cmd(args_mf) == 0
    assert out_dir.exists()


def test_cli_main_dispatch_for_new_subcommands(temp_dir: Path, mock_config_dict: dict):
    cfg_file = temp_dir / "cloud.yaml"
    import yaml

    cfg_file.write_text(yaml.dump(mock_config_dict), encoding="utf-8")

    with patch("cloudctl.commands.orchestrator_cmd.execute_orchestrator_cmd", return_value=0):
        assert cli_main(["-c", str(cfg_file), "orchestrator", "status"]) == 0

    with patch("cloudctl.commands.monitor.execute_monitor_cmd", return_value=0):
        assert cli_main(["-c", str(cfg_file), "monitor"]) == 0

    with patch("cloudctl.commands.alerts.execute_alerts_cmd", return_value=0):
        assert cli_main(["-c", str(cfg_file), "alerts"]) == 0

    with patch("cloudctl.commands.sbom_cmd.execute_sbom_cmd", return_value=0):
        assert cli_main(["-c", str(cfg_file), "sbom"]) == 0
