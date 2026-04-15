"""End-to-end test: run a full pipeline with mock model."""

import pytest
import json
from unittest.mock import AsyncMock

from src.core.config import AppConfig, ModelsConfig, ModelConfig, StorageConfig, ServerConfig
from src.core.engine import Engine
from src.core.state import UserBrief


def _make_mock_model():
    model = AsyncMock()
    call_count = 0

    async def generate(prompt: str, **kwargs):
        nonlocal call_count
        call_count += 1

        # Match by the unique role identifier at the start of each agent's Jinja2 template.
        # Use the most-specific/unique phrase first to avoid partial overlaps.
        if "选题策划专家" in prompt:
            # topic_generator/generate.j2 — "你是一个专业的内容选题策划专家"
            return json.dumps([
                {"title": "AI编程工具大测评", "angle": "横向对比", "score": 9.0, "reasoning": "热门话题"},
                {"title": "程序员必备AI工具", "angle": "推荐清单", "score": 7.5, "reasoning": "实用向"},
            ])
        elif "内容研究员" in prompt:
            # material_collector/collect.j2 — "你是一个专业的内容研究员"
            return json.dumps([
                {"source": "https://example.com/1", "title": "AI Tools 2026", "snippet": "Review data...", "source_type": "web"},
            ])
        elif "内容创作者" in prompt:
            # content_generator/generate.j2 — "你是一个专业的内容创作者"
            return json.dumps({
                "title": "AI编程工具大测评 🔥 5款工具实测对比",
                "body": "最近一个月，我深度体验了5款主流AI编程工具...\n\n1. Cursor - 最强代码补全\n2. Copilot - GitHub生态整合\n3. Claude Code - 最懂上下文",
                "tags": ["AI", "编程工具", "测评"],
                "image_prompts": ["comparison chart of AI coding tools"],
            })
        elif "内容审核专家" in prompt:
            # reviewer/review.j2 — "你是一个专业的内容审核专家"
            return json.dumps({
                "score": 8.5,
                "issues": [],
                "suggestions": ["可以增加具体价格对比"],
            })
        elif "内容运营分析师" in prompt:
            # analyst/analyze.j2 — "你是一个专业的内容运营分析师"
            return json.dumps({
                "summary": "本次内容质量良好，选题热度高",
                "insights": ["AI工具测评类内容持续受关注", "对比形式读者接受度高"],
                "improvement_suggestions": ["增加价格和性能的量化数据"],
            })
        else:
            return json.dumps({"text": "fallback response"})

    model.generate = generate
    model.generate_image = AsyncMock(return_value=b"fake_image_bytes")
    model.close = AsyncMock()
    return model


@pytest.fixture
def test_config(tmp_path):
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "xiaohongshu_image_text.yaml").write_text("""
name: "小红书图文"
description: "测试管道"
platforms: ["xiaohongshu"]
stages:
  - agent: topic_generator
    config:
      style: "测评"
      count: 3
  - agent: material_collector
    config:
      sources: ["web"]
      max_items: 5
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0
  - agent: analyst
    config:
      metrics: ["engagement"]
""")

    config = AppConfig(
        models=ModelsConfig(
            text=ModelConfig(provider="minimax", api_key="test", base_url="http://test", model="test"),
        ),
        storage=StorageConfig(
            db_path=str(tmp_path / "test.db"),
            assets_dir=str(tmp_path / "assets"),
            outputs_dir=str(tmp_path / "outputs"),
        ),
    )
    return config, pipelines_dir


@pytest.mark.asyncio
async def test_full_pipeline_run(test_config):
    config, pipelines_dir = test_config
    engine = Engine(config, pipelines_dir)

    mock_model = _make_mock_model()
    engine.text_model = mock_model

    await engine.initialize()

    for agent_name in ["topic_generator", "material_collector", "content_generator", "reviewer", "analyst"]:
        agent = engine.registry.get(agent_name)
        agent.model = mock_model

    brief = UserBrief(topic="AI编程工具测评", keywords=["AI", "coding"], platform_hints=["xiaohongshu"])
    result = await engine.run_pipeline("xiaohongshu_image_text", brief)

    assert result["status"] == "completed"
    assert result["run_id"]

    assert len(result["topics"]) == 2
    assert result["selected_topic"]["title"] == "AI编程工具大测评"
    assert len(result["materials"]) == 1
    assert "xiaohongshu" in result["contents"]
    assert "xiaohongshu" in result["reviews"]
    assert result["reviews"]["xiaohongshu"]["passed"] is True
    assert result["analysis"]["summary"]

    contents = await engine.state_store.list_contents(run_id=result["run_id"])
    assert len(contents) == 1
    assert contents[0]["platform"] == "xiaohongshu"
    assert contents[0]["status"] == "approved"

    await engine.close()
