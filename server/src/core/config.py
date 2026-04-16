"""Configuration loader — reads YAML, substitutes env vars."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from dotenv import load_dotenv
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 4096


class ModelsConfig(BaseModel):
    text: ModelConfig = Field(default_factory=lambda: ModelConfig(provider="minimax"))
    image: ModelConfig = Field(default_factory=lambda: ModelConfig(provider="minimax"))


class StorageConfig(BaseModel):
    database_url: str = "postgresql://superpipeline:sp2026secure@127.0.0.1:5432/superpipeline"
    assets_dir: str = "data/assets"
    outputs_dir: str = "data/outputs"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _substitute_env_vars(obj: object) -> object:
    """Recursively replace ${VAR_NAME} with os.environ values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return _ENV_VAR_PATTERN.sub(_replace, obj)
    elif isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


def load_config(path: Path) -> AppConfig:
    """Load and validate config from a YAML file."""
    # Load .env from the same directory as the config file (or project root)
    env_file = path.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text())
    resolved = _substitute_env_vars(raw)
    return AppConfig.model_validate(resolved)
