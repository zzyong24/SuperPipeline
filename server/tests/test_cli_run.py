import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.run._run_pipeline")
def test_sp_run_returns_run_id(mock_run):
    mock_run.return_value = {"run_id": "abc123", "status": "completed"}
    result = runner.invoke(app, ["run", "xiaohongshu_image_text", "--brief", "AI tools review", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["run_id"] == "abc123"


@patch("src.cli.commands.status._get_run_status")
def test_sp_status_list(mock_status):
    mock_status.return_value = [
        {"run_id": "abc123", "pipeline_name": "test", "status": "completed", "created_at": "2026-04-15"},
    ]
    result = runner.invoke(app, ["status", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1


@patch("src.cli.commands.status._get_run_detail")
def test_sp_status_single_run(mock_detail):
    mock_detail.return_value = {
        "run_id": "abc123", "pipeline_name": "test", "status": "completed", "stage": "completed",
    }
    result = runner.invoke(app, ["status", "abc123", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["run_id"] == "abc123"
