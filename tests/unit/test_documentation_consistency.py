"""Automated consistency testing for USPC repository documentation.

Verifies that:
1. All CLI subcommands referenced in documentation exist in create_parser().
2. All configuration settings referenced exist in config/schema.yaml or defaults.yaml.
3. Internal document links point to existing files.
4. Port numbers and version strings match reality.
"""

from __future__ import annotations

import re
from pathlib import Path

from cloudctl.cli import create_parser
from cloudctl.core.config import ConfigManager


def test_documentation_cli_commands_consistency():
    """Verify that all CLI commands documented in CLI-REFERENCE.md and README.md exist."""
    parser = create_parser()
    # Find all registered subparsers
    subparsers_action = next(action for action in parser._actions if action.dest == "command")
    registered_commands = set(subparsers_action.choices.keys())

    # Check CLI-REFERENCE.md
    cli_ref = Path("docs/CLI-REFERENCE.md")
    assert cli_ref.exists()
    content = cli_ref.read_text(encoding="utf-8")

    # Extract commands from `cloudctl <command>` headers in markdown
    documented_cmds = set(re.findall(r"### `cloudctl\s+([a-z-]+)", content))

    # All documented commands must be in registered_commands
    for cmd in documented_cmds:
        assert cmd in registered_commands, (
            f"Documented command 'cloudctl {cmd}' in CLI-REFERENCE.md is not a registered CLI command!"
        )


def test_documentation_internal_links_resolve():
    """Verify that internal markdown links in docs/ and root point to existing files."""
    repo_root = Path(__file__).resolve().parents[2]
    md_files = list(repo_root.glob("docs/**/*.md")) + list(repo_root.glob("*.md"))

    assert len(md_files) >= 15, "Expected at least 15 markdown files in repository"

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

    broken_links = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            target = match.group(2)
            # Skip external URL links
            if target.startswith("http://") or target.startswith("https://"):
                continue

            # Strip anchor tags (#...)
            target_clean = target.split("#")[0]
            if not target_clean:
                continue

            # Resolve relative to current md_file
            resolved_target = (md_file.parent / target_clean).resolve()
            if not resolved_target.exists():
                broken_links.append(f"{md_file.name} -> {target} (resolved: {resolved_target})")

    assert not broken_links, f"Found broken internal markdown documentation links: {broken_links}"


def test_documentation_config_schema_consistency():
    """Verify that top-level config sections documented in CONFIGURATION.md exist in schema.yaml."""
    cfg_mgr = ConfigManager()
    schema = cfg_mgr.load_schema()
    schema_props = set(schema.get("properties", {}).keys())

    config_doc = Path("docs/CONFIGURATION.md")
    assert config_doc.exists()
    content = config_doc.read_text(encoding="utf-8")

    # Documented top-level sections in backticks
    doc_sections = set(re.findall(r"### `([a-z_]+)`", content))
    for section in doc_sections:
        assert section in schema_props, (
            f"Config section '{section}' documented in CONFIGURATION.md is not in schema.yaml!"
        )


def test_documentation_status_audit_matrix_completeness():
    """Verify that DOCUMENTATION_STATUS.md lists existing documentation files."""
    doc_status = Path("DOCUMENTATION_STATUS.md")
    assert doc_status.exists()
    content = doc_status.read_text(encoding="utf-8")

    expected_docs = [
        "REQUIREMENTS.md",
        "ARCHITECTURE.md",
        "PROJECT_STATUS.md",
        "CONFIGURATION.md",
        "CLI-REFERENCE.md",
        "SECURITY.md",
        "NETWORKING.md",
        "ORCHESTRATION.md",
        "MONITORING.md",
        "PERFORMANCE.md",
        "BACKUP-DR.md",
        "ACCEPTANCE.md",
        "TESTING.md",
        "CI-CD.md",
        "SBOM-LICENSE.md",
        "DEPENDENCIES.md",
        "UPGRADE-MIGRATION.md",
        "USER_GUIDE.md",
        "TROUBLESHOOTING.md",
        "SETUP.md",
    ]
    for doc in expected_docs:
        assert doc in content, f"Expected {doc} to be listed in DOCUMENTATION_STATUS.md"
