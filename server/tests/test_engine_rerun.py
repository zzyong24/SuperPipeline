"""Tests for Engine.rerun_from_stage()."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.engine import Engine
from src.core.config import AppConfig, ModelsConfig, ModelConfig, StorageConfig
from src.core.state import UserBrief


def _make_config(tmp_path):
    return AppConfig(
        models=ModelsConfig(
            text=ModelConfig(provider="minimax", api_key="test", base_url="http://test", model="test"),
            image=ModelConfig(provider="minimax", api_key="test", base_url="http://test", model="test"),
        ),
        storage=StorageConfig(
            db_path=str(tmp_path / "test.db"),
            assets_dir=str(tmp_path / "assets"),
            outputs_dir=str(tmp_path / "outputs"),
        ),
    )


@pytest.fixture
async def engine(tmp_path):
    """Create engine with mock model that returns valid JSON for all agents."""
    config = _make_config(tmp_path)

    # Create pipelines dir with a test pipeline
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test_pipeline.yaml").write_text('''
name: "测试管道"
description: "测试用"
platforms: ["test"]
stages:
  - agent: topic_generator
    config:
      style: "test"
      count: 2
  - agent: material_collector
    config:
      max_items: 3
  - agent: content_generator
    config:
      platform: test
      format: article
  - agent: reviewer
    config:
      rules: ["quality_score"]
      min_score: 5.0
  - agent: analyst
    config:
      metrics: ["engagement"]
''')

    e = Engine(config, pipelines_dir)
    await e.initialize()

    # Mock model to return appropriate JSON for each agent
    async def mock_generate(prompt, **kwargs):
        if "选题策划专家" in prompt:
            return '[{"title":"Test Topic","angle":"test angle","score":8.5,"reasoning":"good"}]'
        elif "内容研究员" in prompt:
            return '[{"source":"http://test","title":"Material","snippet":"test snippet","source_type":"web"}]'
        elif "内容创作者" in prompt:
            return '{"title":"Test Title","body":"This is test body content that is long enough to pass validation checks","tags":["test"],"image_prompts":["a test image"]}'
        elif "内容审核" in prompt:
            return '{"score":8.0,"issues":[],"suggestions":["good job"]}'
        elif "运营分析" in prompt:
            return '{"summary":"Good content","insights":["insight1"],"improvement_suggestions":["suggestion1"]}'
        return '{"result":"ok"}'

    e.text_model.generate = AsyncMock(side_effect=mock_generate)
    e.text_model.close = AsyncMock()

    yield e
    await e.close()


@pytest.mark.asyncio
async def test_rerun_single_stage_only(engine):
    """Rerun a single stage with only=True."""
    # First, run the full pipeline
    brief = UserBrief(topic="test rerun")
    result = await engine.run_pipeline("test_pipeline", brief)
    run_id = result["run_id"]
    assert result["status"] != "failed", f"Pipeline failed: {result.get('error', result.get('errors'))}"

    # Check snapshots were saved
    snapshots = await engine.state_store.list_snapshots(run_id)
    assert len(snapshots) == 5

    # Rerun only topic_generator
    new_state = await engine.rerun_from_stage(
        run_id, "topic_generator",
        config_overrides={"count": 3},
        only=True,
    )

    # Should have version 2 for topic_generator
    history = await engine.state_store.list_snapshot_history(run_id, "topic_generator")
    assert len(history) == 2
    assert history[1]["version"] == 2

    # Other stages should still be version 1
    cg_history = await engine.state_store.list_snapshot_history(run_id, "content_generator")
    assert len(cg_history) == 1


@pytest.mark.asyncio
async def test_rerun_cascade(engine):
    """Rerun from content_generator cascades to reviewer and analyst."""
    brief = UserBrief(topic="test cascade")
    result = await engine.run_pipeline("test_pipeline", brief)
    run_id = result["run_id"]
    assert result["status"] != "failed"

    # Rerun from content_generator (cascade = default)
    new_state = await engine.rerun_from_stage(
        run_id, "content_generator",
    )

    # content_generator, reviewer, analyst should have version 2
    for agent in ["content_generator", "reviewer", "analyst"]:
        history = await engine.state_store.list_snapshot_history(run_id, agent)
        assert len(history) == 2, f"{agent} should have 2 versions"

    # topic_generator and material_collector should still be version 1
    for agent in ["topic_generator", "material_collector"]:
        history = await engine.state_store.list_snapshot_history(run_id, agent)
        assert len(history) == 1, f"{agent} should have 1 version"


@pytest.mark.asyncio
async def test_rerun_not_found(engine):
    """Rerun with nonexistent run_id raises."""
    with pytest.raises(ValueError, match="not found"):
        await engine.rerun_from_stage("nonexistent", "topic_generator")
