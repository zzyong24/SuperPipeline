import pytest
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_pipeline_list(tmp_path, monkeypatch):
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test.yaml").write_text("name: Test Pipeline\nstages: []")
    monkeypatch.setenv("SP_PIPELINES_DIR", str(pipelines_dir))
    result = runner.invoke(app, ["pipeline", "list"])
    assert result.exit_code == 0
    assert "Test Pipeline" in result.stdout


def test_pipeline_list_json(tmp_path, monkeypatch):
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test.yaml").write_text("name: Test\nstages: []")
    monkeypatch.setenv("SP_PIPELINES_DIR", str(pipelines_dir))
    result = runner.invoke(app, ["pipeline", "list", "--format", "json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert isinstance(data, list)
