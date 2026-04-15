"""WeChat Official Account (微信公众号) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class WechatPlatform(BasePlatform):
    name = "wechat"
    max_text_length = 20000
    max_tags = 0
    max_images = 20

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        if len(body) > self.max_text_length:
            issues.append(f"正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(body) < 200:
            issues.append("正文内容过短，公众号长文建议至少 200 字")
        return issues

    def format_content(self, body: str, **kwargs) -> str:
        return body.strip()

    def get_rules_prompt(self) -> str:
        return (
            "平台：微信公众号。要求：\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 标题要有吸引力，引发点击\n"
            "- 开头设悬念或抛出痛点\n"
            "- 长文深度分析，逻辑层层递进\n"
            "- 适当配图并附图片说明\n"
            "- 结尾引导关注公众号\n"
            f"- 最多 {self.max_images} 张配图\n"
            "- 公众号无话题标签"
        )
