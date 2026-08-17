"""Zenith comprehensive test suite covering all remaining edge cases and branches."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from cloudctl.core.backup import BackupManager
from cloudctl.core.config import ConfigManager, get_repo_root
from cloudctl.core.container import ContainerManager
from cloudctl.core.detect import (
    detect_disks,
    detect_host,
    detect_os,
    detect_privileges,
    detect_virtualization,
)
from cloudctl.core.health import HealthChecker
from cloudctl.core.performance import (
    collect_live_metrics,
    detect_resource_profile,
)
from cloudctl.core.reporting import print_security_report
from cloudctl.core.secrets import SecretManager
from cloudctl.core.security import SecurityChecker
from cloudctl.core.storage import StorageManager
from cloudctl.utils.fs import (
    ensure_directory,
    get_free_disk_space_gb,
    remove_path_safely,
)
from src.media.auth import (
    authenticate_request,
    verify_media_token_user,
)
from src.media.config import MediaConfig
from src.media.models import MediaDatabase, MediaItem
from src.media.scanner import StorageScanner
from src.media.streaming import parse_range_header
from src.media.thumbnails import ThumbnailGenerator
from src.media.transcoder import Transcoder
from src.media.worker import BackgroundWorker


def test_detect_remaining_branches(temp_dir: Path):
    # HostInfo.to_dict()
    host = detect_host()
    d = host.to_dict()
    assert "cpu_cores" in d
    assert "total_ram_gb" in d

    # detect_os arm64 and windows/macos branches
    with (
        patch("platform.system", return_value="Linux"),
        patch("platform.machine", return_value="arm64"),
    ):
        assert detect_os()[3] == "aarch64"

    with patch("platform.system", return_value="Darwin"):
        assert detect_os()[0] == "macos"

    with patch("platform.system", return_value="FreeBSD"):
        assert detect_os()[0] == "freebsd"

    # detect_virtualization WSL proc version reading
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", return_value="Linux version microsoft-standard-WSL2"),
    ):
        assert detect_virtualization("linux") == "wsl2"

    # detect_privileges windows exception
    with patch("cloudctl.core.detect.ctypes", create=True) as mock_ctypes:
        mock_ctypes.windll.shell32.IsUserAnAdmin.side_effect = Exception("error")
        assert detect_privileges("windows") is False

    # detect_disks exception branch
    with patch("psutil.disk_partitions", side_effect=Exception("disk error")):
        assert detect_disks() == []


def test_container_manager_all_missing_branches():
    # Podman engine with pod creation and port mappings
    cm_podman = ContainerManager(engine="podman")
    cm_podman.engine = "podman"
    with patch("cloudctl.core.container.run_command") as mock_run:
        # pod exists = False, then create pod with ports
        mock_run.side_effect = [
            MagicMock(success=False),
            MagicMock(success=True),
        ]
        assert cm_podman.create_pod(port_mappings=[(8080, 80), (8085, 8085)]) is True

    # Docker network create
    cm_docker = ContainerManager(engine="docker")
    cm_docker.engine = "docker"
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.side_effect = [
            MagicMock(success=False),
            MagicMock(success=True),
        ]
        assert cm_docker.create_pod() is True

    # run_container podman branch with extra args, env, volumes, ports
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=True)
        assert (
            cm_podman.run_container(
                name="c_podman",
                image="img:1.0",
                env={"A": "1"},
                volumes=[("/data", "/cont_data")],
                extra_args=["--cap-drop=ALL"],
            )
            is True
        )

    # run_container docker with ports and failure branch
    with patch("cloudctl.core.container.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=False, stderr="Docker daemon error")
        assert (
            cm_docker.run_container(
                name="c_docker",
                image="img:1.0",
                ports=[(80, 80)],
            )
            is False
        )


def test_backup_manager_remaining_branches(mock_config_dict: dict, temp_dir: Path):
    bm = BackupManager(mock_config_dict, secrets_dir=temp_dir / "secrets")

    # init_repository failure
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.side_effect = [
            MagicMock(success=False),  # cat config check
            MagicMock(success=False, stderr="Restic not found"),  # init
        ]
        assert bm.init_repository() is False

    # create_backup failure
    with (
        patch("cloudctl.core.backup.run_command") as mock_run,
        patch.object(bm, "init_repository", return_value=True),
    ):
        mock_run.side_effect = [
            MagicMock(success=False, stdout=""),  # pg_dump
            MagicMock(success=False, stderr="Backup write failed"),  # restic backup
        ]
        assert bm.create_backup(verify_after=True) is False

    # verify_repository failure
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=False, stderr="Integrity corrupted")
        assert bm.verify_repository() is False

    # restore_backup dry-run and failure
    with patch("cloudctl.core.backup.run_command") as mock_run:
        mock_run.return_value = MagicMock(success=False, stderr="Restore error")
        assert bm.restore_backup("snap1", dry_run=True) is False

    # test_restore_isolation failure
    with patch.object(bm, "restore_backup", return_value=False):
        assert bm.test_restore_isolation() is False


def test_config_manager_semantic_validations(temp_dir: Path):
    cm = ConfigManager(config_path=temp_dir / "conf.yaml", repo_root=temp_dir)
    defaults = cm.load_defaults()
    assert isinstance(defaults, dict)

    # Invalid CIDR
    with patch.object(cm, "load_schema", return_value={"type": "object"}):
        with pytest.raises(ValueError) as exc:
            cm.validate({"network": {"vpn_subnet": "invalid_subnet_string"}})
        assert "Invalid VPN CIDR" in str(exc.value)

        # Invalid headscale port
        with pytest.raises(ValueError) as exc:
            cm.validate({"network": {"headscale_port": 999999}})
        assert "Invalid Headscale port" in str(exc.value)

        # Invalid service port
        with pytest.raises(ValueError) as exc:
            cm.validate({"services": {"test_srv": {"port": 0}}})
        assert "Invalid port for service" in str(exc.value)

        # Invalid media port
        with pytest.raises(ValueError) as exc:
            cm.validate({"media": {"enabled": True, "port": -5}})
        assert "Invalid media service port" in str(exc.value)

        # Media port collision with service port
        with pytest.raises(ValueError) as exc:
            cm.validate(
                {
                    "services": {"app": {"port": 8085}},
                    "media": {"enabled": True, "port": 8085},
                }
            )
        assert "Port collision" in str(exc.value)


def test_fs_utilities_all_branches(temp_dir: Path):
    # Ensure directory
    d = ensure_directory(temp_dir / "sub_dir" / "deeper")
    assert d.exists()

    # get_free_disk_space_gb on non-existent path
    free_gb = get_free_disk_space_gb(temp_dir / "non_existent_folder" / "sub")
    assert free_gb > 0

    # remove_path_safely on a symlink or file
    f = temp_dir / "temp_file.txt"
    f.write_text("content", encoding="utf-8")
    assert remove_path_safely(f) is True
    assert not f.exists()


def test_auth_all_legacy_and_edge_branches():
    secret = "jwt_secret_test_999"

    # Legacy 2-part token: expiry:sig
    import hmac
    import time

    expiry = int(time.time()) + 100
    msg = f"item_leg:{expiry}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), "sha256").hexdigest()
    token_2part = f"{expiry}:{sig}"

    valid, user = verify_media_token_user("item_leg", token_2part, secret)
    assert valid is True
    assert user == "default_user"

    # Expired 2-part token
    exp_old = int(time.time()) - 100
    msg_old = f"item_leg:{exp_old}"
    sig_old = hmac.new(secret.encode("utf-8"), msg_old.encode("utf-8"), "sha256").hexdigest()
    token_2part_old = f"{exp_old}:{sig_old}"
    assert verify_media_token_user("item_leg", token_2part_old, secret) == (False, "")

    # verify_media_token_user exception
    assert verify_media_token_user("item_leg", None, secret) == (False, "")

    # authenticate_request with Bearer admin secret
    req_mock = MagicMock()
    req_mock.app.state.config = MediaConfig(jwt_secret=secret)
    req_mock.path_params = {}
    auth_cred = HTTPAuthorizationCredentials(scheme="Bearer", credentials=secret)
    assert authenticate_request(req_mock, auth_header=auth_cred, token=None) is True
    assert req_mock.state.user_id == "admin"

    # authenticate_request failure raises 401
    with pytest.raises(HTTPException) as exc:
        authenticate_request(req_mock, auth_header=None, token="wrong_token")
    assert exc.value.status_code == 401


def test_scanner_edge_cases(temp_dir: Path):
    # Scanner with non-existent data directory
    cfg_non = MediaConfig(data_path=temp_dir / "does_not_exist")
    scanner_non = StorageScanner(cfg_non)
    assert scanner_non.scan() == []

    # Scanner with hidden files and normal files
    data_dir = temp_dir / "scan_data"
    data_dir.mkdir()
    (data_dir / ".hidden.mp4").write_bytes(b"data")
    (data_dir / "good.mp4").write_bytes(b"data")

    cfg = MediaConfig(data_path=data_dir)
    scanner = StorageScanner(cfg)
    items = scanner.scan()
    assert len(items) == 1
    assert items[0].filename == "good.mp4"

    # Symlink escape simulation
    with patch("src.media.scanner.is_safe_path", return_value=False):
        assert scanner.scan() == []


def test_performance_and_benchmark_edge_cases(temp_dir: Path):
    # Resource profile auto detection on various sizes
    with patch("cloudctl.core.performance.detect_host") as mock_host:
        mock_host.return_value = MagicMock(total_ram_gb=1.5, cpu_cores=1)
        assert detect_resource_profile().name == "TINY"

        mock_host.return_value = MagicMock(total_ram_gb=3.5, cpu_cores=2)
        assert detect_resource_profile().name == "SMALL"

        mock_host.return_value = MagicMock(total_ram_gb=7.0, cpu_cores=4)
        assert detect_resource_profile().name == "STANDARD"

        mock_host.return_value = MagicMock(total_ram_gb=14.0, cpu_cores=6)
        assert detect_resource_profile().name == "PERFORMANCE"

        mock_host.return_value = MagicMock(total_ram_gb=32.0, cpu_cores=16)
        assert detect_resource_profile().name == "MEDIA"

    # Live metrics collection bottlenecks
    with (
        patch("psutil.cpu_percent", return_value=92.0),
        patch("psutil.virtual_memory") as mock_mem,
        patch("shutil.disk_usage") as mock_disk,
    ):
        mock_mem.return_value = MagicMock(
            total=8 * (1024**3), available=0.5 * (1024**3), percent=96.0
        )
        mock_disk.return_value = MagicMock(
            total=100 * (1024**3), used=98 * (1024**3), free=2 * (1024**3)
        )

        metrics = collect_live_metrics(temp_dir)
        assert metrics.status == "CRITICAL"
        assert len(metrics.bottlenecks) >= 2


def test_media_models_and_database(temp_dir: Path):
    db_file = temp_dir / "media.db"
    db = MediaDatabase(db_file)

    item = MediaItem(
        id="item1",
        rel_path="vids/vid1.mp4",
        filename="vid1.mp4",
        media_type="video",
        mime_type="video/mp4",
        size_bytes=1024,
        mtime=100.0,
    )
    db.upsert_item(item)

    assert db.get_by_id("item1") is not None
    assert db.get_by_rel_path("vids/vid1.mp4") is not None
    assert db.get_by_rel_path("non_existent") is None

    # Delete
    assert db.delete_by_id("item1") is True
    assert db.delete_by_id("item1") is False


def test_transcoder_and_thumbnails(temp_dir: Path):
    transcoder = Transcoder(temp_dir / "cache", max_concurrency=1)
    assert transcoder.is_browser_native(Path("video.mp4")) is True
    assert transcoder.is_browser_native(Path("video.mkv")) is False

    # Thumbnail generator
    tg = ThumbnailGenerator(temp_dir / "thumbnails", default_width=150)
    img_file = temp_dir / "pic.png"
    from PIL import Image

    im = Image.new("RGB", (100, 100), color=(10, 20, 30))
    im.save(img_file)

    res = tg.generate(img_file, "item_img", "image")
    assert res is not None
    assert res.exists()


def test_storage_manager_deep_branches(temp_dir: Path):
    sm = StorageManager(temp_dir / "st_data", temp_dir / "st_config", min_free_space_gb=999999.0)

    # validate_space insufficient space error
    with pytest.raises(ValueError) as exc:
        sm.validate_space()
    assert "Insufficient disk space" in str(exc.value)

    # verify_read_write content mismatch
    sm.min_free_space_gb = 0.01
    with patch("pathlib.Path.read_text", return_value="mismatched_corrupted_payload"):
        with pytest.raises(IOError) as exc:
            sm.verify_read_write(temp_dir / "st_data")
        assert "verification failed" in str(exc.value)

    # migrate_data identical source and target
    assert sm.migrate_data(temp_dir / "st_data") is True

    # migrate_data target not enough space
    with patch("cloudctl.core.storage.get_free_disk_space_gb", return_value=0.001):
        with pytest.raises(ValueError) as exc:
            sm.migrate_data(temp_dir / "target_dir")
        assert "does not have enough free space" in str(exc.value)


def test_fs_unlink_error_and_subcommands(temp_dir: Path):
    # remove_path_safely when unlink throws OSError
    f_err = temp_dir / "locked_file.txt"
    f_err.write_text("locked", encoding="utf-8")
    with patch("pathlib.Path.unlink", side_effect=OSError("locked by another process")):
        assert remove_path_safely(f_err) is False

    # benchmark command
    from cloudctl.commands.benchmark import execute_benchmark

    args_bm = MagicMock(config=None, profile=None, json=False)
    with patch("cloudctl.commands.benchmark.run_benchmark") as mock_run:
        mock_run.return_value = MagicMock(
            profile_name="STANDARD",
            disk_write_mbs=120.0,
            disk_read_mbs=350.0,
            cpu_score_mops=50.0,
            synthetic_stream_capacity_mbs=240.0,
            recommended_concurrency=15,
            recommended_transcode_jobs=2,
            bottlenecks=["Storage write speed is slow (< 30 MB/s)"],
        )
        assert execute_benchmark(args_bm) == 0

    # doctor command with remediations
    from cloudctl.commands.doctor import execute_doctor

    args_doc = MagicMock(config=None, json=False)
    with patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health:
        from cloudctl.core.health import DiagnosticCheck, SystemHealthReport

        mock_health.return_value = SystemHealthReport(
            overall_status="DEGRADED",
            checks=[
                DiagnosticCheck(
                    component="Runtime",
                    name="Engine",
                    status="DEGRADED",
                    message="Degraded",
                    remediation="Restart engine",
                ),
            ],
            containers=[],
        )
        assert execute_doctor(args_doc) == 1


def test_lifecycle_failure_branches():
    from cloudctl.commands.lifecycle import execute_restart, execute_start, execute_stop

    args = MagicMock(config=None)
    with (
        patch("cloudctl.core.container.ContainerManager.start_container", return_value=False),
        patch("cloudctl.core.container.ContainerManager.stop_container", return_value=False),
        patch("cloudctl.core.container.ContainerManager.restart_container", return_value=False),
    ):
        assert execute_start(args) == 1
        assert execute_stop(args) == 0
        assert execute_restart(args) == 1


def test_install_smoke_test_branch(mock_config_dict: dict, temp_dir: Path):
    from cloudctl.commands.install import execute_install

    cfg_file = temp_dir / "install_cloud.yaml"
    cm = ConfigManager(config_path=cfg_file)
    cm.save_config(mock_config_dict)

    args = MagicMock(config=str(cfg_file), dry_run=False, skip_smoke_test=False)
    with (
        patch("cloudctl.core.container.ContainerManager.run_container", return_value=True),
        patch("cloudctl.core.container.ContainerManager.create_pod", return_value=True),
        patch("cloudctl.core.health.HealthChecker.run_all_checks") as mock_health,
        patch("time.sleep"),
    ):
        mock_health.return_value = MagicMock(overall_status="HEALTHY", checks=[], containers=[])
        assert execute_install(args) == 0


@pytest.mark.asyncio
async def test_worker_and_app_extra_branches(temp_dir: Path):
    cfg = MediaConfig(
        data_path=temp_dir / "w_data",
        cache_path=temp_dir / "w_cache",
        allowed_origins=["http://localhost:3000", "http://127.0.0.1:8080"],
    )
    db = MediaDatabase(cfg.db_path)
    worker = BackgroundWorker(config=cfg, db=db, interval_seconds=1)

    # Worker start and immediate stop
    await worker.start()
    worker.trigger_scan()
    await worker.stop()

    # Re-start when already running
    await worker.start()
    await worker.start()  # should return early
    await worker.stop()


def test_streaming_and_thumbnails_exact_branches(temp_dir: Path):
    # parse_range_header edge cases
    assert parse_range_header("bytes=", 1000) == (0, 999)

    with pytest.raises(HTTPException) as exc:
        parse_range_header("bytes=-0", 1000)
    assert exc.value.status_code == 416

    # Thumbnail exists cache hit
    tg = ThumbnailGenerator(temp_dir / "th_cache", default_width=100)
    dest = tg.get_thumbnail_path("cached_item")
    dest.write_bytes(b"cached_thumb")
    assert tg.generate(temp_dir / "pic.jpg", "cached_item", "image") == dest

    # Security checker edge branches
    cfg = {
        "network": {"mode": "private"},
        "cloud": {"admin_user": "customadmin"},
        "runtime": {"rootless": False},
        "backup": {"enabled": False},
        "security": {"tls_enabled": False},
    }
    sc = SecurityChecker(cfg, temp_dir)
    assert sc.check_container_privileges().status == "WARN"
    assert sc.check_backup_encryption().status == "WARN"


def test_config_and_secrets_edge_branches(temp_dir: Path):
    import jsonschema

    cm = ConfigManager(config_path=temp_dir / "c.yaml")
    with (
        patch.object(cm, "load_schema", return_value={"type": "object"}),
        patch(
            "jsonschema.validate",
            side_effect=jsonschema.exceptions.ValidationError("Schema violation"),
        ),
    ):
        with pytest.raises(ValueError) as exc:
            cm.validate({"version": "0.1.0"})
        assert "Configuration error" in str(exc.value)

    # get_repo_root fallback
    with patch("pathlib.Path.exists", return_value=False):
        assert get_repo_root() is not None

    # SecretManager load corrupted json
    sm = SecretManager(secrets_dir=temp_dir / "corrupt_sec")
    sm.secrets_file.parent.mkdir(parents=True, exist_ok=True)
    sm.secrets_file.write_text("not_valid_json_content", encoding="utf-8")
    sec = sm.load_or_generate_secrets()
    assert sec.postgres_password is not None

    # Performance cmd with bottlenecks
    from cloudctl.commands.performance_cmd import execute_performance

    args_p = MagicMock(config=None, json=False)
    with patch("cloudctl.commands.performance_cmd.collect_live_metrics") as mock_m:
        from cloudctl.core.performance import LivePerformanceMetrics

        mock_m.return_value = LivePerformanceMetrics(
            cpu_percent=95.0,
            ram_percent=92.0,
            ram_used_gb=14.0,
            ram_total_gb=16.0,
            disk_free_gb=1.0,
            disk_used_percent=99.0,
            active_streams=10,
            queue_depth=2,
            bottlenecks=["High CPU (>85%)", "Low Disk (<5GB)"],
            status="CRITICAL",
        )
        assert execute_performance(args_p) == 0


def test_health_and_security_deep_branches(mock_config_dict: dict, temp_dir: Path):
    hc = HealthChecker(mock_config_dict)

    # Container status stopped and unhealthy
    with (
        patch("cloudctl.core.container.ContainerManager.is_available", return_value=True),
        patch("cloudctl.core.container.ContainerManager.get_container_status") as mock_cs,
        patch("cloudctl.core.storage.get_free_disk_space_gb", return_value=0.5),
    ):
        from cloudctl.core.container import ContainerStatus

        mock_cs.side_effect = [
            ContainerStatus(
                name="uspc-nextcloud",
                id="1",
                image="img",
                status="stopped",
                health="none",
                ports=[],
                created_at="now",
            ),
            ContainerStatus(
                name="uspc-postgres",
                id="2",
                image="img",
                status="error",
                health="none",
                ports=[],
                created_at="now",
            ),
            ContainerStatus(
                name="uspc-redis",
                id="3",
                image="img",
                status="running",
                health="healthy",
                ports=[],
                created_at="now",
            ),
            ContainerStatus(
                name="uspc-headscale",
                id="4",
                image="img",
                status="running",
                health="healthy",
                ports=[],
                created_at="now",
            ),
            ContainerStatus(
                name="uspc-media",
                id="5",
                image="img",
                status="running",
                health="healthy",
                ports=[],
                created_at="now",
            ),
        ]
        rep = hc.run_all_checks()
        assert rep.overall_status == "UNHEALTHY"

    # Security check report with FAIL and strict mode
    from cloudctl.core.security import SecurityCheckResult

    results_fail = [
        SecurityCheckResult(name="TLS", status="FAIL", details="No TLS", remediation="Enable TLS"),
    ]
    assert print_security_report(results_fail, strict=True) == 1
    assert print_security_report(results_fail, strict=False) == 1
