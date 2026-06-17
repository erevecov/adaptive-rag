from typer.testing import CliRunner

from adaptive_rag.cli.app import app


def test_cli_version_command():
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "adaptive-rag 0.1.0" in result.stdout


def test_cli_health_command():
    runner = CliRunner()

    result = runner.invoke(app, ["health"])

    assert result.exit_code == 0
    assert "ok" in result.stdout
