import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.models import ModelAdapter, MiniMaxAdapter, create_model_adapter
from src.core.config import ModelConfig


def test_create_model_adapter_minimax():
    config = ModelConfig(
        provider="minimax",
        api_key="test-key",
        base_url="https://api.minimax.chat/v1",
        model="abab6.5-chat",
    )
    adapter = create_model_adapter(config)
    assert isinstance(adapter, MiniMaxAdapter)


def test_create_model_adapter_unknown_provider():
    config = ModelConfig(provider="unknown_provider", api_key="test")
    with pytest.raises(ValueError, match="Unknown model provider"):
        create_model_adapter(config)


@pytest.mark.asyncio
async def test_minimax_adapter_generate():
    config = ModelConfig(
        provider="minimax",
        api_key="test-key",
        base_url="https://api.minimax.chat/v1",
        model="abab6.5-chat",
    )
    adapter = MiniMaxAdapter(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello world"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_response):
        result = await adapter.generate("Say hello")
        assert result == "Hello world"
