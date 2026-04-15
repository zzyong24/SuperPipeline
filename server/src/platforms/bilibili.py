"""Bilibili (B站) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class BilibiliPlatform(BasePlatform):
    name = "bilibili"
    max_text_length = 10000
    max_tags = 10
    max_images = 20

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])
        if len(body) > self.max_text_length:
            issues.append(f"正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(body) < 100:
            issues.append("正文内容过短，建议至少 100 字")
        if len(tags) > self.max_tags:
            issues.append(f"标签数 {len(tags)} 超过限制 {self.max_tags}")
        return issues

    def format_content(self, body: str, **kwargs) -> str:
        tags = kwargs.get("tags", [])
        formatted = body.strip()
        if tags:
            tag_line = " ".join(f"#{t}" for t in tags)
            formatted = f"{formatted}\n\n{tag_line}"
        return formatted

    def get_rules_prompt(self) -> str:
        return (
            "平台：B站专栏。要求：\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 干货/教程/深度向内容\n"
            "- 段落清晰，用小标题分块\n"
            "- 数据支撑观点，逻辑严谨\n"
            f"- 最多 {self.max_tags} 个话题标签\n"
            f"- 最多 {self.max_images} 张配图"
        )
