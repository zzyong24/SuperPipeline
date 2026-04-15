import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.agent._list_agents")
def test_agent_list(mock_list):
    mock_list.return_value = [
        {"name": "topic_generator", "consumes": ["user_brief"], "produces": ["topics", "selected_topic"], "config_schema": "TopicGenConfig"},
    ]
    result = runner.invoke(app, ["agent", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["name"] == "topic_generator"


@patch("src.cli.commands.agent._list_agents")
def test_agent_list_table(mock_list):
    mock_list.return_value = [
        {"name": "topic_generator", "consumes": ["user_brief"], "produces": ["topics"], "config_schema": "TopicGenConfig"},
    ]
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code == 0
    assert "topic_generator" in result.stdout
