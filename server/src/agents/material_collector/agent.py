"""Material Collector Agent — gathers reference materials for a topic."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json, extract_json
from src.agents.material_collector.schemas import MaterialCollectConfig
from src.core.state import Material, Topic


class MaterialCollectorAgent(BaseAgent):
    name = "material_collector"
    consumes = ["selected_topic"]
    produces = ["materials"]
    config_schema = MaterialCollectConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: MaterialCollectConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])

        prompt = self.get_prompt(
            "collect.j2",
            cfg,
            title=topic.title,
            angle=topic.angle,
            max_items=cfg.max_items,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_materials = json.loads(extract_json(response))
            if not isinstance(raw_materials, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse materials response: {e}\nRaw: {response[:500]}") from e

        materials = [Material.model_validate(m).model_dump() for m in raw_materials]
        return {"materials": materials}
