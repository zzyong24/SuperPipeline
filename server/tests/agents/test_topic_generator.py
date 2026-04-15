import pytest
import json
from unittest.mock import AsyncMock
from src.agents.topic_generator.agent import TopicGeneratorAgent
from src.agents.topic_generator.schemas import TopicGenConfig
from src.core.state import UserBrief


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps([
        {"title": "AI编程工具横评", "angle": "测评对比", "score": 8.5, "reasoning": "热门话题"},
        {"title": "程序员效率提升指南", "angle": "实用技巧", "score": 7.0, "reasoning": "常青选题"},
    ]))
    return model


def test_topic_generator_metadata():
    assert TopicGeneratorAgent.name == "topic_generator"
    assert TopicGeneratorAgent.consumes == ["user_brief"]
    assert TopicGeneratorAgent.produces == ["topics", "selected_topic"]


@pytest.mark.asyncio
async def test_topic_generator_run(mock_model):
    agent = TopicGeneratorAgent(model=mock_model)
    config = TopicGenConfig(style="种草", count=5)
    inputs = {"user_brief": UserBrief(topic="AI tools", keywords=["AI", "coding"]).model_dump()}

    result = await agent.run(inputs, config)

    assert "topics" in result
    assert "selected_topic" in result
    assert len(result["topics"]) == 2
    assert result["selected_topic"]["title"] == "AI编程工具横评"
    mock_model.generate.assert_called_once()


@pytest.mark.asyncio
async def test_topic_generator_handles_bad_json(mock_model):
    mock_model.generate = AsyncMock(return_value="not valid json")
    agent = TopicGeneratorAgent(model=mock_model)
    config = TopicGenConfig()
    inputs = {"user_brief": UserBrief(topic="test").model_dump()}

    with pytest.raises(ValueError, match="parse"):
        await agent.run(inputs, config)
