"""Pipeline YAML config loader."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.state import PipelineConfig


def load_pipeline(path: Path) -> PipelineConfig:
    """Load a pipeline config from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")
    raw = yaml.safe_load(path.read_text())
    return PipelineConfig.model_validate(raw)


def list_pipelines(directory: Path) -> list[dict]:
    """List all pipeline configs in a directory."""
    pipelines = []
    for yaml_file in sorted(directory.glob("*.yaml")):
        try:
            config = load_pipeline(yaml_file)
            pipelines.append({
                "name": config.name,
                "description": config.description,
                "platforms": config.platforms,
                "stages": len(config.stages),
                "file": yaml_file.name,
            })
        except Exception:
            continue
    return pipelines
