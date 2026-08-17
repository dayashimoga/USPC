"""USPC Unified Command-Line Interface (cloudctl)."""

from __future__ import annotations

import argparse
import sys

from cloudctl import __version__
from cloudctl.core.logging import setup_logger


def create_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for all cloudctl commands."""
    parser = argparse.ArgumentParser(
        prog="cloudctl",
        description="Universal Personal Cloud Platform (USPC) Control Tool",
        epilog="For documentation and issues, visit https://github.com/uspc-project/uspc",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"cloudctl v{__version__}",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to custom cloud.yaml configuration file",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity level (default: INFO)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON logs",
    )

    subparsers = parser.add_subparsers(dest="command", title="Commands", metavar="<command>")

    # setup
    setup_parser = subparsers.add_parser(
        "setup", help="One-command bootstrap and complete environment setup"
    )
    setup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate environment and plan without modifying system",
    )
    setup_parser.add_argument(
        "--non-interactive", action="store_true", help="Run in non-interactive unattended mode"
    )
    setup_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing configuration/secrets"
    )
    setup_parser.add_argument("--name", type=str, help="Cloud instance identifier")
    setup_parser.add_argument("--domain", type=str, help="Cloud instance domain")
    setup_parser.add_argument(
        "--skip-smoke-test", action="store_true", help="Skip post-installation smoke tests"
    )

    # init
    init_parser = subparsers.add_parser(
        "init", help="Initialize configuration and security credentials"
    )
    init_parser.add_argument(
        "--force", "-f", action="store_true", help="Overwrite existing configuration"
    )
    init_parser.add_argument("--name", type=str, help="Cloud instance name")
    init_parser.add_argument("--domain", type=str, help="Domain or hostname")

    # install
    install_parser = subparsers.add_parser(
        "install", help="Full automated one-command installation"
    )
    install_parser.add_argument(
        "--dry-run", action="store_true", help="Validate and plan without applying changes"
    )
    install_parser.add_argument(
        "--skip-smoke-test", action="store_true", help="Skip post-installation smoke tests"
    )

    # start
    subparsers.add_parser("start", help="Start all cloud containers and services")

    # stop
    subparsers.add_parser("stop", help="Stop all cloud containers and services")

    # restart
    subparsers.add_parser("restart", help="Restart all cloud containers and services")

    # status
    status_parser = subparsers.add_parser(
        "status", help="Display health status dashboard of all services"
    )
    status_parser.add_argument("--json", action="store_true", help="Output status in JSON format")

    # doctor
    doctor_parser = subparsers.add_parser(
        "doctor", help="Run diagnostic health checks with remediation advice"
    )
    doctor_parser.add_argument(
        "--fix", action="store_true", help="Attempt automatic remediation of detected issues"
    )

    # update
    update_parser = subparsers.add_parser(
        "update", help="Perform safe system and container updates with rollback"
    )
    update_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate update without applying changes"
    )

    # backup
    backup_parser = subparsers.add_parser("backup", help="Create encrypted Restic backup snapshot")
    backup_parser.add_argument(
        "--verify", action="store_true", help="Verify cryptographic integrity of backup repository"
    )
    backup_parser.add_argument("--tag", type=str, default="manual", help="Backup tag/label")

    # restore
    restore_parser = subparsers.add_parser(
        "restore", help="Restore cloud state from encrypted backup snapshot"
    )
    restore_parser.add_argument(
        "--snapshot", type=str, default="latest", help="Snapshot ID to restore (default: latest)"
    )
    restore_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate restore without modifying active files"
    )
    restore_parser.add_argument(
        "--test", action="store_true", help="Test restore into isolated temporary directory"
    )

    # migrate
    migrate_parser = subparsers.add_parser(
        "migrate", help="Export or import portable migration bundle"
    )
    migrate_sub = migrate_parser.add_subparsers(dest="migrate_action", required=True)

    migrate_export = migrate_sub.add_parser("export", help="Export migration bundle")
    migrate_export.add_argument(
        "--output", "-o", type=str, required=True, help="Destination archive path (.tar.gz)"
    )

    migrate_import = migrate_sub.add_parser("import", help="Import migration bundle")
    migrate_import.add_argument(
        "--input", "-i", type=str, required=True, help="Source bundle archive path"
    )

    # uninstall
    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Cleanly remove USPC services and runtime"
    )
    uninstall_parser.add_argument(
        "--purge-data", action="store_true", help="Purge all user data and backups (CAUTION)"
    )
    uninstall_parser.add_argument(
        "--force", "-f", action="store_true", help="Bypass confirmation prompt"
    )

    # logs
    logs_parser = subparsers.add_parser("logs", help="Stream or display aggregated service logs")
    logs_parser.add_argument(
        "--service",
        "-s",
        type=str,
        help="Specific service (nextcloud, postgres, redis, media, headscale)",
    )
    logs_parser.add_argument(
        "--tail", "-n", type=int, default=100, help="Number of recent log lines to display"
    )
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow live log output")

    # security-check
    sec_parser = subparsers.add_parser(
        "security-check", help="Run comprehensive security audit checks"
    )
    sec_parser.add_argument("--strict", action="store_true", help="Fail if any warning is detected")

    # test
    test_parser = subparsers.add_parser("test", help="Execute automated test suite")
    test_parser.add_argument(
        "--media-only", action="store_true", help="Run media library test suite only"
    )
    test_parser.add_argument(
        "--coverage", action="store_true", help="Generate code coverage report"
    )

    # performance
    perf_parser = subparsers.add_parser(
        "performance", help="Display live system metrics, active users, and capacity"
    )
    perf_parser.add_argument("--json", action="store_true", help="Output metrics in JSON format")

    # benchmark
    bench_parser = subparsers.add_parser(
        "benchmark", help="Measure practical disk/compute capacity and bottleneck report"
    )
    bench_parser.add_argument(
        "--profile",
        type=str,
        choices=["tiny", "small", "standard", "performance", "media"],
        help="Force specific profile",
    )
    bench_parser.add_argument(
        "--stress", action="store_true", help="Execute progressive concurrency stress workload test"
    )
    bench_parser.add_argument("--json", action="store_true", help="Output benchmark in JSON format")

    # cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean cache, temporary files, and stale transcode assets"
    )
    cleanup_parser.add_argument(
        "--dry-run", action="store_true", help="Report reclaimable space without deleting"
    )
    cleanup_parser.add_argument(
        "--purge-thumbnails", action="store_true", help="Purge cached thumbnail assets"
    )
    cleanup_parser.add_argument(
        "--purge-transcodes", action="store_true", help="Purge cached transcoded videos"
    )

    # bundle
    bundle_parser = subparsers.add_parser("bundle", help="Create offline installation package")
    bundle_sub = bundle_parser.add_subparsers(dest="bundle_action", required=True)
    bundle_create = bundle_sub.add_parser("create", help="Create offline bundle package")
    bundle_create.add_argument(
        "--output", "-o", type=str, default="uspc-offline-bundle.tar.gz", help="Output path"
    )

    # readiness
    readiness_parser = subparsers.add_parser(
        "readiness", help="Comprehensive production readiness verification and compliance check"
    )
    readiness_parser.add_argument(
        "--json", action="store_true", help="Output readiness audit in JSON format"
    )

    # acceptance
    acceptance_parser = subparsers.add_parser(
        "acceptance",
        help="Run automated production acceptance audit and print final verdict report",
    )
    acceptance_parser.add_argument(
        "--json", action="store_true", help="Output acceptance audit report in JSON format"
    )
    acceptance_parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        help="Export acceptance.json and acceptance.html to directory",
    )

    # config
    config_parser = subparsers.add_parser(
        "config", help="Declarative configuration management and validation"
    )
    config_sub = config_parser.add_subparsers(dest="config_action", required=True)
    config_sub.add_parser("validate", help="Validate current configuration against schema")
    config_sub.add_parser(
        "diff", help="Display configuration overrides and provenance (AUTO vs DEFAULT vs USER)"
    )
    config_export = config_sub.add_parser("export", help="Export active configuration")
    config_export.add_argument("--output", "-o", type=str, help="Output destination path")
    config_export.add_argument(
        "--unmask-secrets", action="store_true", help="Include raw secrets (CAUTION)"
    )
    config_import = config_sub.add_parser("import", help="Import external configuration")
    config_import.add_argument(
        "--input", "-i", type=str, required=True, help="Input configuration path"
    )
    config_migrate = config_sub.add_parser(
        "migrate", help="Migrate configuration to a newer version"
    )
    config_migrate.add_argument(
        "--target-version",
        type=str,
        default="0.3.0",
        help="Target configuration version (default: 0.3.0)",
    )

    # Add --config argument to all subparsers so `cloudctl init -c path` also works
    for sp in subparsers.choices.values():
        sp.add_argument(
            "--config",
            "-c",
            type=str,
            default=None,
            help="Path to custom cloud.yaml configuration file",
        )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI execution dispatch."""
    parser = create_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Setup logger
    setup_logger(
        level=getattr(args, "log_level", "INFO"),
        json_format=getattr(args, "json", False),
    )

    if not args.command:
        parser.print_help()
        return 1

    # Dispatch to appropriate command module
    try:
        if args.command == "setup":
            from cloudctl.commands.setup import execute_setup

            return execute_setup(args)
        elif args.command == "init":
            from cloudctl.commands.init import execute_init

            return execute_init(args)
        elif args.command == "install":
            from cloudctl.commands.install import execute_install

            return execute_install(args)
        elif args.command == "start":
            from cloudctl.commands.lifecycle import execute_start

            return execute_start(args)
        elif args.command == "stop":
            from cloudctl.commands.lifecycle import execute_stop

            return execute_stop(args)
        elif args.command == "restart":
            from cloudctl.commands.lifecycle import execute_restart

            return execute_restart(args)
        elif args.command == "status":
            from cloudctl.commands.status import execute_status

            return execute_status(args)
        elif args.command == "doctor":
            from cloudctl.commands.doctor import execute_doctor

            return execute_doctor(args)
        elif args.command == "performance":
            from cloudctl.commands.performance_cmd import execute_performance

            return execute_performance(args)
        elif args.command == "benchmark":
            from cloudctl.commands.benchmark import execute_benchmark

            return execute_benchmark(args)
        elif args.command == "update":
            from cloudctl.commands.update import execute_update

            return execute_update(args)
        elif args.command == "backup":
            from cloudctl.commands.backup import execute_backup

            return execute_backup(args)
        elif args.command == "restore":
            from cloudctl.commands.restore import execute_restore

            return execute_restore(args)
        elif args.command == "migrate":
            from cloudctl.commands.migrate import execute_migrate

            return execute_migrate(args)
        elif args.command == "uninstall":
            from cloudctl.commands.uninstall import execute_uninstall

            return execute_uninstall(args)
        elif args.command == "cleanup":
            from cloudctl.commands.cleanup import execute_cleanup

            return execute_cleanup(args)
        elif args.command == "logs":
            from cloudctl.commands.logs import execute_logs

            return execute_logs(args)
        elif args.command == "security-check":
            from cloudctl.commands.security_check import execute_security_check

            return execute_security_check(args)
        elif args.command == "test":
            from cloudctl.commands.test_cmd import execute_test

            return execute_test(args)
        elif args.command == "bundle":
            from cloudctl.commands.bundle import execute_bundle

            return execute_bundle(args)
        elif args.command == "config":
            from cloudctl.commands.config_cmd import execute_config

            return execute_config(args)
        elif args.command == "readiness":
            from cloudctl.commands.readiness_cmd import execute_readiness

            return execute_readiness(args)
        elif args.command == "acceptance":
            from cloudctl.commands.acceptance import execute_acceptance

            return execute_acceptance(args)
        else:
            parser.print_help()
            return 1

    except Exception as e:
        sys.stderr.write(f"\n[FATAL ERROR] {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
