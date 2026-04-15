import pytest
import json
from unittest.mock import AsyncMock
from src.agents.analyst.agent import AnalystAgent
from src.agents.analyst.schemas import AnalystConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "summary": "本次内容整体质量良好",
        "insights": ["AI工具类内容受众广", "对比形式效果好"],
        "improvement_suggestions": ["增加实际使用截图", "加入价格对比"],
    }))
    return model


def test_analyst_metadata():
    assert AnalystAgent.name == "analyst"
    assert "contents" in AnalystAgent.consumes
    assert "reviews" in AnalystAgent.consumes
    assert AnalystAgent.produces == ["analysis"]


@pytest.mark.asyncio
async def test_analyst_run(mock_model):
    agent = AnalystAgent(model=mock_model)
    config = AnalystConfig(metrics=["engagement", "reach"])
    inputs = {
        "contents": {"xiaohongshu": {"platform": "xiaohongshu", "title": "Test", "body": "Body", "tags": []}},
        "reviews": {"xiaohongshu": {"platform": "xiaohongshu", "passed": True, "score": 8.0, "issues": [], "suggestions": []}},
    }

    result = await agent.run(inputs, config)

    assert "analysis" in result
    assert result["analysis"]["summary"] == "本次内容整体质量良好"
    assert len(result["analysis"]["insights"]) == 2
