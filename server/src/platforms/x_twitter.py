"""X (Twitter) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class XPlatform(BasePlatform):
    name = "x"
    max_text_length = 280
    max_tags = 5
    max_images = 4

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])
        if len(body) > self.max_text_length:
            issues.append(f"推文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(tags) > self.max_tags:
            issues.append(f"标签数 {len(tags)} 超过限制 {self.max_tags}")
        return issues

    def format_content(self, body: str, **kwargs) -> str:
        tags = kwargs.get("tags", [])
        formatted = body.strip()
        if tags:
            tag_line = " ".join(f"#{t}" for t in tags[:self.max_tags])
            if len(formatted) + len(tag_line) + 2 <= self.max_text_length:
                formatted = f"{formatted}\n\n{tag_line}"
        return formatted

    def get_rules_prompt(self) -> str:
        return (
            "平台：X (Twitter)。要求：\n"
            f"- 每条推文不超过 {self.max_text_length} 字符\n"
            "- 简洁有力，观点鲜明\n"
            f"- 最多 {self.max_tags} 个话题标签\n"
            f"- 最多 {self.max_images} 张配图\n"
            "- 用提问或犀利观点引发互动"
        )
