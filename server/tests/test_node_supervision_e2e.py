"""End-to-end integration test for the node supervision system."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock
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
    """Engine with mock model + test pipeline."""
    config = _make_config(tmp_path)
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test_e2e.yaml").write_text('''
name: "E2E测试管道"
description: "节点监督E2E测试"
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

    call_count = {"content_generator": 0}

    async def mock_generate(prompt, **kwargs):
        # Order matters: match most specific keyword first to avoid cross-matching
        if "选题策划专家" in prompt:
            return '[{"title":"Test Topic","angle":"test angle","score":8.5,"reasoning":"good"}]'
        elif "内容研究员" in prompt:
            return '[{"source":"http://test","title":"Material","snippet":"test snippet","source_type":"web"}]'
        elif "内容创作者" in prompt:
            call_count["content_generator"] += 1
            n = call_count["content_generator"]
            return json.dumps({
                "title": f"Title v{n}",
                "body": f"Body content version {n} that is long enough for validation",
                "tags": ["test", f"v{n}"],
                "image_prompts": ["test image"]
            })
        elif "内容审核专家" in prompt:
            return '{"score":8.0,"issues":[],"suggestions":["good"]}'
        elif "运营分析师" in prompt:
            return '{"summary":"Analysis","insights":["insight"],"improvement_suggestions":["suggestion"]}'
        return '{"result":"ok"}'

    e.text_model.generate = AsyncMock(side_effect=mock_generate)
    e.text_model.close = AsyncMock()

    yield e
    await e.close()


@pytest.mark.asyncio
async def test_full_node_supervision_flow(engine):
    """Full E2E: run → snapshots → edit → rerun → cascade verification."""

    # ===== Step 1: Run pipeline =====
    brief = UserBrief(topic="节点监督测试")
    result = await engine.run_pipeline("test_e2e", brief)
    run_id = result["run_id"]
    assert result["status"] != "failed", f"Pipeline failed: {result}"

    # ===== Step 2: Verify all 5 snapshots saved =====
    snapshots = await engine.state_store.list_snapshots(run_id)
    assert len(snapshots) == 5, f"Expected 5 snapshots, got {len(snapshots)}"

    agents = [s["agent"] for s in snapshots]
    assert "topic_generator" in agents
    assert "content_generator" in agents
    assert "reviewer" in agents

    for snap in snapshots:
        assert snap["version"] == 1
        assert snap["status"] == "completed"
        assert snap["duration_ms"] >= 0

    # ===== Step 3: Check snapshot content =====
    tg_snap = await engine.state_store.get_snapshot(run_id, "topic_generator")
    assert tg_snap is not None
    assert "user_brief" in tg_snap["inputs"]
    assert "topics" in tg_snap["outputs"]

    cg_snap = await engine.state_store.get_snapshot(run_id, "content_generator")
    assert cg_snap is not None
    assert cg_snap["outputs"]["contents"]["test"]["title"] == "Title v1"

    # ===== Step 4: Edit content_generator output =====
    edited_outputs = dict(cg_snap["outputs"])
    edited_outputs["contents"]["test"]["title"] = "Edited Title"
    await engine.state_store.update_snapshot_outputs(run_id, "content_generator", 1, edited_outputs)

    # Verify edit persisted
    edited_snap = await engine.state_store.get_snapshot(run_id, "content_generator", version=1)
    assert edited_snap["outputs"]["contents"]["test"]["title"] == "Edited Title"

    # ===== Step 5: Rerun from content_generator (cascade) =====
    new_state = await engine.rerun_from_stage(run_id, "content_generator")

    # content_generator should now be version 2 with "Title v2"
    cg_history = await engine.state_store.list_snapshot_history(run_id, "content_generator")
    assert len(cg_history) == 2
    assert cg_history[0]["version"] == 1  # original (edited)
    assert cg_history[1]["version"] == 2  # rerun
    assert cg_history[1]["outputs"]["contents"]["test"]["title"] == "Title v2"

    # Downstream stages should also be version 2
    for agent in ["reviewer", "analyst"]:
        history = await engine.state_store.list_snapshot_history(run_id, agent)
        assert len(history) == 2, f"{agent} should have 2 versions after cascade"

    # Upstream stages should still be version 1
    for agent in ["topic_generator", "material_collector"]:
        history = await engine.state_store.list_snapshot_history(run_id, agent)
        assert len(history) == 1, f"{agent} should still have 1 version"

    # ===== Step 6: Verify run state updated =====
    updated_run = await engine.state_store.get_run(run_id)
    assert updated_run["status"] == "completed"
    assert updated_run["state"]["contents"]["test"]["title"] == "Title v2"

    # ===== Step 7: Single rerun (only=True) =====
    await engine.rerun_from_stage(run_id, "analyst", only=True)

    analyst_history = await engine.state_store.list_snapshot_history(run_id, "analyst")
    assert len(analyst_history) == 3  # original + cascade + only rerun

    # Reviewer should still be at version 2 (not affected by only=True)
    reviewer_history = await engine.state_store.list_snapshot_history(run_id, "reviewer")
    assert len(reviewer_history) == 2


@pytest.mark.asyncio
async def test_rerun_with_config_override(engine):
    """Rerun with config overrides."""
    brief = UserBrief(topic="配置覆盖测试")
    result = await engine.run_pipeline("test_e2e", brief)
    run_id = result["run_id"]
    assert result["status"] != "failed"

    # Rerun topic_generator with different count
    await engine.rerun_from_stage(
        run_id, "topic_generator",
        config_overrides={"count": 10},
        only=True,
    )

    history = await engine.state_store.list_snapshot_history(run_id, "topic_generator")
    assert len(history) == 2
    # The config of version 2 should have count=10
    v2 = history[1]
    assert v2["config"]["agent_config"]["count"] == 10
