"""Content Generator Agent — creates platform-specific content with multi-source image strategy."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.content_generator.schemas import ContentGenConfig
from src.core.state import PlatformContent, Topic, Material, ExtractedImage, ImageSource, InlineImageSpec

# Load topic_tag_map at module level for reuse
_TAG_MAP_PATH = Path(__file__).parent / "topic_tag_map.json"
_TAG_MAP: dict | None = None


def _load_tag_map() -> dict:
    global _TAG_MAP
    if _TAG_MAP is None:
        if _TAG_MAP_PATH.exists():
            with open(_TAG_MAP_PATH, "r", encoding="utf-8") as f:
                _TAG_MAP = json.load(f)
        else:
            _TAG_MAP = {"topic_tag_strategies": {}, "_default_strategy": {}}
    return _TAG_MAP


def _get_topic_key_and_strategy(topic_title: str, topic_angle: str) -> tuple[str, str]:
    """Determine topic_key from topic title/angle and build tag strategy string."""
    tag_map = _load_tag_map()
    strategies = tag_map.get("topic_tag_strategies", {})
    default_strategy = tag_map.get("_default_strategy", {})

    # Try to match topic_title or topic_angle against known topic_keys
    topic_key = None
    matched_strategy = None

    # Check angle first (more specific)
    for key in strategies:
        if key in topic_angle or topic_angle in key:
            topic_key = key
            matched_strategy = strategies[key]
            break

    # Check title
    if topic_key is None:
        for key in strategies:
            if key in topic_title or topic_title in key:
                topic_key = key
                matched_strategy = strategies[key]
                break

    # Fallback to default
    if topic_key is None:
        topic_key = "通用内容"
        matched_strategy = default_strategy

    # Build strategy string
    core_tags = matched_strategy.get("core_tags", [])
    hot_tags = matched_strategy.get("hot_tags", [])
    audience_tags = matched_strategy.get("audience_tags", [])
    hashtag_style = matched_strategy.get("hashtag_style", "")

    tag_strategy = f"""基于话题类型「{topic_key}」的标签策略：
- 核心标签（必选，3-5个）：{', '.join(core_tags[:5])}
- 热点标签（可选，1-2个）：{', '.join(hot_tags[:2]) if hot_tags else '无'}
- 受众标签（精准覆盖）：{', '.join(audience_tags[:3])}
- 推荐 Hashtag 格式：{hashtag_style}
- 标签总计：5-8个，不要超过10个"""

    return topic_key, tag_strategy


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

        # Get topic_key and tag strategy
        topic_key, tag_strategy = _get_topic_key_and_strategy(topic.title, topic.angle)

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
            topic_key=topic_key,
            materials=[m.model_dump() for m in materials],
            platform_rules=platform_rules,
            style=cfg.style,
            extracted_images=[i.model_dump() for i in extracted_images],
            doc_synth_summary=doc_synth_output.get("summary", ""),
            previous_review_issues=previous_issues,
            review_iteration=review_iteration,
            tag_strategy=tag_strategy,
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
