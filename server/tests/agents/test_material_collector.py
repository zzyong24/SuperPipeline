import pytest
import json
from unittest.mock import AsyncMock
from src.agents.material_collector.agent import MaterialCollectorAgent
from src.agents.material_collector.schemas import MaterialCollectConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps([
        {"source": "https://example.com/article1", "title": "AI Tools Overview", "snippet": "A comprehensive review...", "source_type": "web"},
        {"source": "https://example.com/article2", "title": "Coding with AI", "snippet": "How AI changes...", "source_type": "web"},
    ]))
    return model


def test_material_collector_metadata():
    assert MaterialCollectorAgent.name == "material_collector"
    assert MaterialCollectorAgent.consumes == ["selected_topic"]
    assert MaterialCollectorAgent.produces == ["materials"]


@pytest.mark.asyncio
async def test_material_collector_run(mock_model):
    agent = MaterialCollectorAgent(model=mock_model)
    config = MaterialCollectConfig(sources=["web"], max_items=10)
    inputs = {"selected_topic": {"title": "AI Tools Review", "angle": "comparison", "score": 8.5}}

    result = await agent.run(inputs, config)

    assert "materials" in result
    assert len(result["materials"]) == 2
    assert result["materials"][0]["source_type"] == "web"
