"""CLI tests via Typer's CliRunner.

Every path here is CI-safe: `--help`, `--version`, listing, argument validation, and
the `estimate` verb (which touches no AWS account). No test triggers a live scan.
"""

from typer.testing import CliRunner

from costhive import __version__
from costhive.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_tools_lists_all_six():
    result = runner.invoke(app, ["tools"])
    assert result.exit_code == 0
    for name in ("steampipe", "custodian", "komiser", "cloudquery", "opencost", "infracost"):
        assert name in result.stdout


def test_scan_and_estimate_help():
    for verb in ("scan", "estimate"):
        result = runner.invoke(app, [verb, "--help"])
        assert result.exit_code == 0
        assert verb in result.stdout


def test_scan_rejects_unknown_tool_before_touching_aws():
    result = runner.invoke(app, ["scan", "--tools", "steampipe,bogus", "--yes"])
    assert result.exit_code == 2
    assert "Unknown" in result.stdout


def test_scan_rejects_unknown_category():
    result = runner.invoke(app, ["scan", "--categories", "idle,notacategory", "--yes"])
    assert result.exit_code == 2
    assert "Unknown categories" in result.stdout


def test_scan_rejects_unknown_format():
    result = runner.invoke(app, ["scan", "--format", "html,docx", "--yes"])
    assert result.exit_code == 2
    assert "Unknown format" in result.stdout


def test_scan_rejects_infracost_as_scan_tool():
    result = runner.invoke(app, ["scan", "--tools", "infracost", "--yes"])
    assert result.exit_code == 2


def test_estimate_runs_without_aws(tmp_path):
    # infracost binary is absent in CI -> tool is SKIPPED, run still succeeds.
    result = runner.invoke(app, ["estimate", "--path", str(tmp_path), "--out", str(tmp_path), "--format", "md"])
    assert result.exit_code == 0
    assert (tmp_path / "report.md").exists()
