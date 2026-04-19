"""Model adapters — pluggable interface for text/image generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from src.core.config import ModelConfig


class ModelAdapter(ABC):
    """Base interface for all model providers."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """Generate an image from a prompt. Returns raw bytes."""

    async def close(self) -> None:
        """Cleanup resources."""


class MiniMaxAdapter(ModelAdapter):
    """MiniMax API adapter (Anthropic-compatible messages endpoint)."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=120.0,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        payload: dict = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        response = await self._client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        # Anthropic format: content is a list of blocks
        content_blocks = data.get("content", [])
        # Extract text blocks, skip thinking blocks
        text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
        return "\n".join(text_parts)

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        # MiniMax image generation uses a separate endpoint
        payload: dict = {
            "model": self.config.model,
            "prompt": prompt,
        }
        if "size" in kwargs:
            payload["size"] = kwargs["size"]

        response = await self._client.post("/v1/images/generations", json=payload)
        response.raise_for_status()
        data = response.json()
        image_url = data["data"][0]["url"]
        img_response = await self._client.get(image_url)
        img_response.raise_for_status()
        return img_response.content

    async def generate_image_caption(self, image_path: str, prompt: str = "") -> str:
        """Use MiniMax vision API to caption an image."""
        import base64
        from pathlib import Path

        img_bytes = Path(image_path).read_bytes()
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": f"data:{mime};base64,{b64}"},
                        {"type": "text", "text": prompt or "描述这张图片的内容，用于文章配图。简短50字以内。"},
                    ],
                }
            ],
            "max_tokens": 200,
        }
        response = await self._client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()
        content_blocks = data.get("content", [])
        text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
        return "\n".join(text_parts)

    async def close(self) -> None:
        await self._client.aclose()


class OpenAICompatibleAdapter(ModelAdapter):
    """Adapter for any OpenAI-compatible API (future use)."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=60.0,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        raise NotImplementedError("Image generation not supported for this provider")

    async def close(self) -> None:
        await self._client.aclose()


_ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    "minimax": MiniMaxAdapter,
    "openai_compatible": OpenAICompatibleAdapter,
}


def create_model_adapter(config: ModelConfig) -> ModelAdapter:
    """Factory function — create a ModelAdapter from config."""
    adapter_cls = _ADAPTER_REGISTRY.get(config.provider)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown model provider: '{config.provider}'. "
            f"Available: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls(config)
