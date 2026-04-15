"""Base platform adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BasePlatform(ABC):
    name: str
    max_text_length: int
    max_tags: int = 30
    max_images: int = 9

    @abstractmethod
    def validate(self, content: dict) -> list[str]:
        """Validate content against platform rules. Returns list of issues."""

    @abstractmethod
    def format_content(self, body: str, **kwargs) -> str:
        """Format raw content to platform conventions."""

    def get_rules_prompt(self) -> str:
        return f"Platform: {self.name}, max {self.max_text_length} chars, max {self.max_tags} tags, max {self.max_images} images."


_PLATFORM_REGISTRY: dict[str, type[BasePlatform]] = {}


def register_platform(cls: type[BasePlatform]) -> type[BasePlatform]:
    _PLATFORM_REGISTRY[cls.name] = cls
    return cls


def get_platform(name: str) -> BasePlatform:
    cls = _PLATFORM_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown platform: '{name}'. Available: {list(_PLATFORM_REGISTRY.keys())}")
    return cls()


def list_platforms() -> list[str]:
    return list(_PLATFORM_REGISTRY.keys())
