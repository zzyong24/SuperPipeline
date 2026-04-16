"""Content Generator Agent — creates platform-specific content with multi-source image strategy."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.content_generator.schemas import ContentGenConfig
from src.core.state import PlatformContent, Topic, Material, ExtractedImage, ImageSource, InlineImageSpec


class ContentGeneratorAgent(BaseAgent):
    name = "content_generator"
    consumes = ["selected_topic", "materials", "extracted_images", "previous_review_issues", "review_iteration"]
    produces = ["contents"]
    config_schema = ContentGenConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ContentGenConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])
        materials = [Material.model_validate(m) for m in inputs.get("materials", [])]
        extracted_images = [ExtractedImage.model_validate(i) for i in inputs.get("extracted_images", [])]
        doc_synth_output = inputs.get("document_synthesizer_output", {})
        previous_issues = inputs.get("previous_review_issues", [])
        review_iteration = inputs.get("review_iteration", 0)

        try:
            from src.platforms.base import get_platform
            platform = get_platform(cfg.platform)
            platform_rules = platform.get_rules_prompt()
        except ValueError:
            platform_rules = f"Platform: {cfg.platform}"

        prompt = self.get_prompt(
            "generate.j2",
            cfg,
            platform=cfg.platform,
            format=cfg.format,
            topic_title=topic.title,
            topic_angle=topic.angle,
            materials=[m.model_dump() for m in materials],
            platform_rules=platform_rules,
            style=cfg.style,
            extracted_images=[i.model_dump() for i in extracted_images],
            doc_synth_summary=doc_synth_output.get("summary", ""),
            previous_review_issues=previous_issues,
            review_iteration=review_iteration,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_content = json.loads(extract_json(response))
            if not isinstance(raw_content, dict):
                raise ValueError("Expected a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse content generation response: {e}\nRaw: {response[:500]}") from e

        # Build image_sources from extracted images
        image_sources = []
        for img in extracted_images:
            image_sources.append(ImageSource(
                image_path=img.image_path,
                source_type="extracted",
                source_detail=img.source_doc_path,
            ).model_dump())

        # Parse inline_images specs if returned by model
        inline_images = []
        for spec_data in raw_content.get("inline_images", []):
            try:
                spec = InlineImageSpec.model_validate(spec_data)
                inline_images.append(spec.model_dump())
            except Exception:
                pass

        content = PlatformContent(
            platform=cfg.platform,
            title=raw_content.get("title", ""),
            body=raw_content.get("body", ""),
            tags=raw_content.get("tags", []),
            image_paths=[img.image_path for img in extracted_images],
            image_prompts=raw_content.get("image_prompts", []),
            image_sources=image_sources,
            inline_images=inline_images,
        )

        return {"contents": {cfg.platform: content.model_dump()}}
