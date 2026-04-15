"""Analyst Agent — post-publish analytics and improvement suggestions."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.analyst.schemas import AnalystConfig
from src.core.state import Analysis


class AnalystAgent(BaseAgent):
    name = "analyst"
    consumes = ["contents", "reviews"]
    produces = ["analysis"]
    config_schema = AnalystConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: AnalystConfig = config

        prompt = self.load_prompt(
            "analyze.j2",
            contents=inputs.get("contents", {}),
            reviews=inputs.get("reviews", {}),
            metrics=cfg.metrics,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_analysis = json.loads(response.strip())
        except (json.JSONDecodeError, ValueError):
            raw_analysis = {
                "summary": "Analysis failed to parse",
                "insights": [],
                "improvement_suggestions": [],
            }

        analysis = Analysis.model_validate(raw_analysis)
        return {"analysis": analysis.model_dump()}
