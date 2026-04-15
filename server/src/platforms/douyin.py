"""Douyin (抖音) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class DouyinPlatform(BasePlatform):
    name = "douyin"
    max_text_length = 2200
    max_tags = 20
    max_images = 9

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])
        if len(body) > self.max_text_length:
            issues.append(f"正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(body) < 50:
            issues.append("正文内容过短，建议至少 50 字")
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
            "平台：抖音。要求：\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 口语化表达，节奏感强\n"
            "- 开头用 hook 吸引注意力\n"
            "- 分段清晰，善用 emoji\n"
            "- 结尾引导互动（点赞、评论、关注）\n"
            f"- 最多 {self.max_tags} 个话题标签\n"
            f"- 最多 {self.max_images} 张配图"
        )
