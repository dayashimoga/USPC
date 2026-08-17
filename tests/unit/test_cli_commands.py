"""Unit tests for cloudctl CLI dispatch and subcommands."""

from pathlib import Path

from cloudctl.cli import create_parser, main


def test_cli_parser_creation():
    parser = create_parser()
    assert parser.prog == "cloudctl"

    # Test argument parsing on various subcommands
    args_init = parser.parse_args(["init", "--force", "--name", "mytestcloud"])
    assert args_init.command == "init"
    assert args_init.name == "mytestcloud"
    assert args_init.force is True

    args_install = parser.parse_args(["install", "--dry-run"])
    assert args_install.command == "install"
    assert args_install.dry_run is True

    args_status = parser.parse_args(["status", "--json"])
    assert args_status.command == "status"
    assert args_status.json is True

    args_doctor = parser.parse_args(["doctor", "--fix"])
    assert args_doctor.command == "doctor"
    assert args_doctor.fix is True

    args_backup = parser.parse_args(["backup", "--verify"])
    assert args_backup.command == "backup"
    assert args_backup.verify is True

    args_restore = parser.parse_args(["restore", "--dry-run"])
    assert args_restore.command == "restore"
    assert args_restore.dry_run is True

    args_migrate = parser.parse_args(["migrate", "export", "-o", "bundle.tar.gz"])
    assert args_migrate.command == "migrate"
    assert args_migrate.migrate_action == "export"

    args_logs = parser.parse_args(["logs", "-s", "media", "-n", "50"])
    assert args_logs.command == "logs"
    assert args_logs.service == "media"
    assert args_logs.tail == 50

    args_sec = parser.parse_args(["security-check", "--strict"])
    assert args_sec.command == "security-check"
    assert args_sec.strict is True


def test_cli_execution_help_and_dry_run(temp_dir: Path):
    cfg_file = temp_dir / "cloud.yaml"
    # CLI without args shows help
    res_empty = main([])
    assert res_empty == 1

    # CLI init
    res_init = main(["init", "-c", str(cfg_file), "--force"])
    assert res_init == 0

    # CLI install dry-run
    res_dry_run = main(["install", "-c", str(cfg_file), "--dry-run"])
    assert res_dry_run == 0

    # CLI security check
    res_sec = main(["security-check", "-c", str(cfg_file)])
    assert res_sec in (0, 1)
