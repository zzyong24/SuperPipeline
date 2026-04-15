import pytest
import json
from unittest.mock import AsyncMock
from src.agents.content_generator.agent import ContentGeneratorAgent
from src.agents.content_generator.schemas import ContentGenConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "title": "AI编程工具大测评 🔥",
        "body": "最近用了好几款AI编程工具...\n\n1. Cursor\n2. Copilot\n3. Claude Code",
        "tags": ["AI", "编程", "工具测评"],
        "image_prompts": ["A comparison chart of AI coding tools"],
    }))
    return model


def test_content_generator_metadata():
    assert ContentGeneratorAgent.name == "content_generator"
    assert "selected_topic" in ContentGeneratorAgent.consumes
    assert "materials" in ContentGeneratorAgent.consumes
    assert ContentGeneratorAgent.produces == ["contents"]


@pytest.mark.asyncio
async def test_content_generator_run(mock_model):
    agent = ContentGeneratorAgent(model=mock_model)
    config = ContentGenConfig(platform="xiaohongshu", format="image_text")
    inputs = {
        "selected_topic": {"title": "AI Tools Review", "angle": "comparison", "score": 8.5},
        "materials": [{"source": "https://example.com", "title": "Ref", "snippet": "data", "source_type": "web"}],
    }

    result = await agent.run(inputs, config)

    assert "contents" in result
    assert "xiaohongshu" in result["contents"]
    content = result["contents"]["xiaohongshu"]
    assert content["platform"] == "xiaohongshu"
    assert len(content["title"]) > 0
    assert len(content["body"]) > 0
