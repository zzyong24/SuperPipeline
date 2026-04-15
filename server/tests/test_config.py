import os
import pytest
from pathlib import Path
from src.core.config import load_config, AppConfig


def test_load_config_from_yaml(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
models:
  text:
    provider: minimax
    api_key: "test-key-123"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-chat"
    max_tokens: 4096
  image:
    provider: minimax
    api_key: "test-key-456"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-image"

storage:
  db_path: "data/superpipeline.db"
  assets_dir: "data/assets"
  outputs_dir: "data/outputs"

server:
  host: "0.0.0.0"
  port: 8000
""")
    config = load_config(config_file)
    assert isinstance(config, AppConfig)
    assert config.models.text.provider == "minimax"
    assert config.models.text.api_key == "test-key-123"
    assert config.storage.db_path == "data/superpipeline.db"
    assert config.server.port == 8000


def test_load_config_env_var_substitution(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "env-secret-key")
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
models:
  text:
    provider: minimax
    api_key: "${MINIMAX_API_KEY}"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-chat"
    max_tokens: 4096
storage:
  db_path: "data/test.db"
  assets_dir: "data/assets"
  outputs_dir: "data/outputs"
server:
  host: "0.0.0.0"
  port: 8000
""")
    config = load_config(config_file)
    assert config.models.text.api_key == "env-secret-key"


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))
