"""Reviewer Agent — AI-powered content quality review with self-correction loop support."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.reviewer.schemas import ReviewerConfig
from src.core.state import PlatformContent, ReviewResult
from src.platforms.base import get_platform


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    consumes = ["contents", "previous_review_issues", "review_iteration"]
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

            prompt = self.get_prompt(
                "review.j2",
                cfg,
                platform=platform_name,
                title=content.title,
                body=content.body,
                tags=content.tags,
                image_count=len(content.image_paths),
                platform_rules=platform_rules,
                rules=cfg.rules,
                # Pass previous issues for targeted correction
                previous_issues=inputs.get("previous_review_issues", []),
            )

            response = await self.model.generate(prompt, temperature=cfg.temperature)

            try:
                raw_review = json.loads(extract_json(response))
            except (json.JSONDecodeError, ValueError):
                raw_review = {"score": 0.0, "issues": ["Failed to parse review"], "suggestions": []}

            score = raw_review.get("score", 0.0)
            all_issues = platform_issues + raw_review.get("issues", [])

            # Add ❌ prefix to platform hard issues (already prefixed by platform.validate)
            # Add ❌ prefix to serious/moderate issues from AI review
            tagged_issues = []
            for issue in all_issues:
                if issue.startswith("❌"):
                    tagged_issues.append(issue)
                elif "【严重】" in issue or "【中等】" in issue:
                    tagged_issues.append(f"❌ {issue}")
                else:
                    tagged_issues.append(issue)

            # Mark hard issues (❌) from platform validation
            hard_issues = [issue for issue in tagged_issues if issue.startswith("❌")]
            passed = score >= cfg.min_score and len(hard_issues) == 0

            review = ReviewResult(
                platform=platform_name,
                passed=passed,
                score=score,
                issues=tagged_issues,
                suggestions=raw_review.get("suggestions", []),
            )
            reviews[platform_name] = review.model_dump()

        # Increment iteration and collect hard issues for content_generator correction
        current_iteration = inputs.get("review_iteration", 0)
        next_iteration = current_iteration + 1

        # Gather all ❌ hard issues across platforms for the correction loop
        all_hard_issues = []
        for platform_name, review_data in reviews.items():
            for issue in review_data.get("issues", []):
                if issue.startswith("❌"):
                    all_hard_issues.append(f"[{platform_name}] {issue}")

        return {
            "reviews": reviews,
            "review_iteration": next_iteration,
            "previous_review_issues": all_hard_issues,
        }
