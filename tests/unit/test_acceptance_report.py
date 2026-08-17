"""Tests for automated production-acceptance report generation (cloudctl acceptance)."""

import argparse
from unittest.mock import MagicMock, patch

from cloudctl.commands.acceptance import execute_acceptance, generate_acceptance_report


def test_generate_acceptance_report(tmp_path):
    """Verify generate_acceptance_report compiles all 6 layers and automated capability gates."""
    with patch("cloudctl.commands.acceptance.evaluate_readiness") as mock_eval:
        mock_eval.return_value = MagicMock(
            verdict="PRODUCTION_READY",
            score_percent=98.5,
            layers={
                "infrastructure": "PASS",
                "application": "PASS",
                "security": "PASS",
                "recovery": "PASS",
                "observability": "PASS",
                "external_remote": "PASS",
            },
        )

        rep = generate_acceptance_report()
        assert rep.overall_status == "ACCEPTED"
        assert rep.readiness_score == 98.5
        assert len(rep.layers) == 6
        assert rep.verifications["one_command_setup"] == "PASS"


def test_execute_acceptance_cli_json_and_text(capsys):
    """Verify cloudctl acceptance CLI runs in both text and JSON modes."""
    with patch("cloudctl.commands.acceptance.evaluate_readiness") as mock_eval:
        mock_eval.return_value = MagicMock(
            verdict="READY",
            score_percent=92.0,
            layers={
                "infrastructure": "PASS",
                "application": "PASS",
                "security": "PASS",
                "recovery": "PASS",
                "observability": "PASS",
                "external_remote": "PASS",
            },
        )

        args_text = argparse.Namespace(json=False, config=None, output_dir=None)
        rc_text = execute_acceptance(args_text)
        assert rc_text == 0

        captured_text = capsys.readouterr()
        assert "USPC FINAL PRODUCTION-ACCEPTANCE AUDIT REPORT" in captured_text.out

        args_json = argparse.Namespace(json=True, config=None, output_dir=None)
        rc_json = execute_acceptance(args_json)
        assert rc_json == 0
        captured_json = capsys.readouterr()
        assert '"overall_status": "ACCEPTED"' in captured_json.out


def test_execute_acceptance_export_html_and_json(tmp_path):
    """Verify cloudctl acceptance exports acceptance.json and acceptance.html files."""
    with patch("cloudctl.commands.acceptance.evaluate_readiness") as mock_eval:
        mock_eval.return_value = MagicMock(
            verdict="PRODUCTION_READY",
            score_percent=99.0,
            layers={
                "infrastructure": "PASS",
                "application": "PASS",
                "security": "PASS",
                "recovery": "PASS",
                "observability": "PASS",
                "external_remote": "PASS",
            },
        )

        out_dir = tmp_path / "reports"
        args = argparse.Namespace(json=False, config=None, output_dir=str(out_dir))
        rc = execute_acceptance(args)
        assert rc == 0

        json_file = out_dir / "acceptance.json"
        html_file = out_dir / "acceptance.html"
        assert json_file.exists()
        assert html_file.exists()

        json_content = json_file.read_text(encoding="utf-8")
        assert '"overall_status": "ACCEPTED"' in json_content
        html_content = html_file.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html_content
        assert "USPC Production-Acceptance Report" in html_content


def test_execute_acceptance_full_lab_workflow(tmp_path):
    """Verify cloudctl acceptance --full executes complete sandbox lab and generates evidence."""
    with patch("cloudctl.commands.install.execute_install", return_value=0):
        with patch("cloudctl.commands.acceptance.evaluate_readiness") as mock_eval:
            mock_eval.return_value = MagicMock(
                verdict="PRODUCTION_READY",
                score_percent=100.0,
                layers={
                    "infrastructure": "PASS",
                    "application": "PASS",
                    "security": "PASS",
                    "recovery": "PASS",
                    "observability": "PASS",
                    "external_remote": "PASS",
                },
            )

            out_dir = tmp_path / "lab_reports"
            args = argparse.Namespace(full=True, json=False, config=None, output_dir=str(out_dir))
            rc = execute_acceptance(args)
            assert rc == 0

            assert (out_dir / "acceptance.json").exists()
            assert (out_dir / "acceptance.html").exists()
