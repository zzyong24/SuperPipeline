"""Reviewer Agent — AI-powered content quality review."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.reviewer.schemas import ReviewerConfig
from src.core.state import PlatformContent, ReviewResult
from src.platforms.base import get_platform


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    consumes = ["contents"]
    produces = ["reviews"]
    config_schema = ReviewerConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ReviewerConfig = config
        contents: dict[str, dict] = inputs.get("contents", {})
        reviews: dict[str, dict] = {}

        for platform_name, content_data in contents.items():
            content = PlatformContent.model_validate(content_data)

            try:
                platform = get_platform(platform_name)
                platform_issues = platform.validate(content_data)
                platform_rules = platform.get_rules_prompt()
            except ValueError:
                platform_issues = []
                platform_rules = ""

            prompt = self.load_prompt(
                "review.j2",
                platform=platform_name,
                title=content.title,
                body=content.body,
                tags=content.tags,
                platform_rules=platform_rules,
                rules=cfg.rules,
            )

            response = await self.model.generate(prompt, temperature=cfg.temperature)

            try:
                raw_review = json.loads(response.strip())
            except (json.JSONDecodeError, ValueError):
                raw_review = {"score": 0.0, "issues": ["Failed to parse review"], "suggestions": []}

            score = raw_review.get("score", 0.0)
            all_issues = platform_issues + raw_review.get("issues", [])
            passed = score >= cfg.min_score and len(platform_issues) == 0

            review = ReviewResult(
                platform=platform_name,
                passed=passed,
                score=score,
                issues=all_issues,
                suggestions=raw_review.get("suggestions", []),
            )
            reviews[platform_name] = review.model_dump()

        return {"reviews": reviews}
