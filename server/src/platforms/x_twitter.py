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
            issues.append(f"Tweet length {len(body)} exceeds {self.max_text_length} limit")
        if len(tags) > self.max_tags:
            issues.append(f"Too many hashtags: {len(tags)}, max {self.max_tags}")
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
            "Platform: X (Twitter). Requirements:\n"
            f"- Max {self.max_text_length} characters per tweet\n"
            "- Be concise and punchy\n"
            f"- Max {self.max_tags} hashtags\n"
            f"- Max {self.max_images} images\n"
            "- Engage with questions or hot takes"
        )
