import pytest
import json
from unittest.mock import AsyncMock
from src.agents.reviewer.agent import ReviewerAgent
from src.agents.reviewer.schemas import ReviewerConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "score": 8.5,
        "issues": [],
        "suggestions": ["可以增加更多数据支撑"],
    }))
    return model


def test_reviewer_metadata():
    assert ReviewerAgent.name == "reviewer"
    assert ReviewerAgent.consumes == ["contents"]
    assert ReviewerAgent.produces == ["reviews"]


@pytest.mark.asyncio
async def test_reviewer_passes_good_content(mock_model):
    agent = ReviewerAgent(model=mock_model)
    config = ReviewerConfig(min_score=7.0)
    inputs = {
        "contents": {
            "xiaohongshu": {
                "platform": "xiaohongshu",
                "title": "Good Title",
                "body": "A well written article about AI tools that meets all requirements and is long enough.",
                "tags": ["AI"],
                "image_paths": [],
            }
        }
    }

    result = await agent.run(inputs, config)

    assert "reviews" in result
    assert "xiaohongshu" in result["reviews"]
    review = result["reviews"]["xiaohongshu"]
    assert review["passed"] is True
    assert review["score"] == 8.5


@pytest.mark.asyncio
async def test_reviewer_fails_low_score(mock_model):
    mock_model.generate = AsyncMock(return_value=json.dumps({
        "score": 4.0,
        "issues": ["内容质量不足"],
        "suggestions": ["重写"],
    }))
    agent = ReviewerAgent(model=mock_model)
    config = ReviewerConfig(min_score=7.0)
    inputs = {
        "contents": {
            "xiaohongshu": {
                "platform": "xiaohongshu",
                "title": "Bad",
                "body": "Short content that is still at least twenty characters long for validation",
                "tags": [],
                "image_paths": [],
            }
        }
    }

    result = await agent.run(inputs, config)
    review = result["reviews"]["xiaohongshu"]
    assert review["passed"] is False
