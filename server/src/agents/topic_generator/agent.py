"""Topic Generator Agent — generates candidate topics from a user brief."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.topic_generator.schemas import TopicGenConfig
from src.core.state import Topic, UserBrief


class TopicGeneratorAgent(BaseAgent):
    name = "topic_generator"
    consumes = ["user_brief"]
    produces = ["topics", "selected_topic"]
    config_schema = TopicGenConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: TopicGenConfig = config
        brief = UserBrief.model_validate(inputs["user_brief"])

        prompt = self.load_prompt(
            "generate.j2",
            topic=brief.topic,
            keywords=brief.keywords,
            style=cfg.style or brief.style,
            platform_hints=brief.platform_hints,
            count=cfg.count,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_topics = json.loads(response.strip())
            if not isinstance(raw_topics, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse topic generation response: {e}") from e

        topics = [Topic.model_validate(t).model_dump() for t in raw_topics]
        selected = max(topics, key=lambda t: t.get("score", 0)) if topics else None

        return {"topics": topics, "selected_topic": selected}
