import pytest
from pathlib import Path
from src.core.pipeline_loader import load_pipeline, list_pipelines
from src.core.state import PipelineConfig


def test_load_pipeline_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "test_pipeline.yaml"
    yaml_file.write_text("""
name: "Test Pipeline"
description: "A test pipeline"
platforms: ["xiaohongshu"]
stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
""")
    config = load_pipeline(yaml_file)
    assert isinstance(config, PipelineConfig)
    assert config.name == "Test Pipeline"
    assert len(config.stages) == 2
    assert config.stages[0].agent == "topic_generator"
    assert config.stages[0].config["style"] == "种草"


def test_load_pipeline_not_found():
    with pytest.raises(FileNotFoundError):
        load_pipeline(Path("/nonexistent.yaml"))


def test_list_pipelines(tmp_path: Path):
    (tmp_path / "pipeline_a.yaml").write_text("name: A\nstages: []")
    (tmp_path / "pipeline_b.yaml").write_text("name: B\nstages: []")
    (tmp_path / "not_yaml.txt").write_text("ignore me")

    pipelines = list_pipelines(tmp_path)
    assert len(pipelines) == 2
    names = {p["name"] for p in pipelines}
    assert names == {"A", "B"}
