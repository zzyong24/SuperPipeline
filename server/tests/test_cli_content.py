import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.content._list_contents")
def test_content_list(mock_list):
    mock_list.return_value = [
        {"content_id": "c1", "platform": "xiaohongshu", "title": "Test", "status": "approved"},
    ]
    result = runner.invoke(app, ["content", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1


@patch("src.cli.commands.content._get_content")
def test_content_get(mock_get):
    mock_get.return_value = {
        "content_id": "c1", "platform": "xiaohongshu", "title": "AI Tools",
        "body": "Full content body here", "status": "approved",
    }
    result = runner.invoke(app, ["content", "get", "c1", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["content_id"] == "c1"


@patch("src.cli.commands.content._get_content")
def test_content_get_copy_mode(mock_get):
    mock_get.return_value = {
        "content_id": "c1", "title": "Title", "body": "Body text for copy", "tags": ["AI"],
    }
    result = runner.invoke(app, ["content", "get", "c1", "--copy"])
    assert result.exit_code == 0
    assert "Title" in result.stdout
    assert "Body text for copy" in result.stdout
