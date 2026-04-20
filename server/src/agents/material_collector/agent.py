"""Material Collector Agent — gathers reference materials for a topic.

When source_documents are available in state, this agent skips web search
and instead marks the source_type of those documents.
"""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.material_collector.schemas import MaterialCollectConfig
from src.core.state import Material, Topic, SourceDocument


class MaterialCollectorAgent(BaseAgent):
    name = "material_collector"
    consumes = ["selected_topic", "source_documents"]
    produces = ["materials"]
    config_schema = MaterialCollectConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: MaterialCollectConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])

        # If source_documents exist and non-empty, skip web search — use documents as materials
        source_documents: list[dict] = inputs.get("source_documents", [])
        if source_documents:
            docs = [SourceDocument.model_validate(d) for d in source_documents]
            materials = [
                Material(
                    source=doc.file_path,
                    title=doc.title or doc.file_path.split("/")[-1],
                    snippet=doc.content[:500] if doc.content else "",
                    source_type="document",
                    source_url=doc.file_path,
                ).model_dump()
                for doc in docs
                if doc.content
            ]
            if materials:
                return {"materials": materials}

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
        # Ensure web materials have source_url
        for m in materials:
            if m.get("source_type") == "web" and not m.get("source_url"):
                m["source_url"] = m.get("source", "")
        return {"materials": materials}
