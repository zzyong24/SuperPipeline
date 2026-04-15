"""Xiaohongshu (小红书) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class XiaohongshuPlatform(BasePlatform):
    name = "xiaohongshu"
    max_text_length = 1000
    max_tags = 30
    max_images = 9

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])
        if len(body) > self.max_text_length:
            issues.append(f"正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(body) < 20:
            issues.append("正文内容过短，建议至少 20 字")
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
            "平台：小红书。要求：\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 标题要有吸引力，可用 emoji\n"
            "- 正文分段清晰，善用列表\n"
            "- 结尾加话题标签\n"
            f"- 最多 {self.max_images} 张配图\n"
            "- 风格：真实分享、种草、干货向"
        )
