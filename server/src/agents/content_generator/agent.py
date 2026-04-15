"""Content Generator Agent — creates platform-specific content."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.content_generator.schemas import ContentGenConfig
from src.core.state import PlatformContent, Topic, Material
from src.platforms.base import get_platform


class ContentGeneratorAgent(BaseAgent):
    name = "content_generator"
    consumes = ["selected_topic", "materials"]
    produces = ["contents"]
    config_schema = ContentGenConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ContentGenConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])
        materials = [Material.model_validate(m) for m in inputs.get("materials", [])]

        try:
            platform = get_platform(cfg.platform)
            platform_rules = platform.get_rules_prompt()
        except ValueError:
            platform_rules = f"Platform: {cfg.platform}"

        prompt = self.load_prompt(
            "generate.j2",
            platform=cfg.platform,
            format=cfg.format,
            topic_title=topic.title,
            topic_angle=topic.angle,
            materials=[m.model_dump() for m in materials],
            platform_rules=platform_rules,
            style=cfg.style,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_content = json.loads(response.strip())
            if not isinstance(raw_content, dict):
                raise ValueError("Expected a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse content generation response: {e}") from e

        content = PlatformContent(
            platform=cfg.platform,
            title=raw_content.get("title", ""),
            body=raw_content.get("body", ""),
            tags=raw_content.get("tags", []),
            image_paths=[],
            image_prompts=raw_content.get("image_prompts", []),
        )

        return {"contents": {cfg.platform: content.model_dump()}}
