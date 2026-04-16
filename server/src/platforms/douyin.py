"""Douyin (抖音) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class DouyinPlatform(BasePlatform):
    name = "douyin"
    max_text_length = 2200
    max_tags = 20
    max_images = 9

    def validate(self, content: dict) -> list[str]:
        """抖音硬性审核条件，任何一项不满足都无法发布。"""
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])
        image_sources = content.get("image_sources", [])
        image_paths = content.get("image_paths", [])

        # 硬性下限（标红项）
        if len(body) < 2000:
            issues.append(f"❌ 抖音硬性要求：正文不得少于 2000 字，当前仅 {len(body)} 字，差 {2000 - len(body)} 字")
        if len(image_paths) < 3:
            issues.append(f"❌ 抖音硬性要求：配图不得少于 3 张，当前仅 {len(image_paths)} 张，差 {3 - len(image_paths)} 张")

        # 软性上限
        if len(body) > self.max_text_length:
            issues.append(f"⚠️ 正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(tags) > self.max_tags:
            issues.append(f"⚠️ 标签数 {len(tags)} 超过限制 {self.max_tags}")
        if len(image_paths) > self.max_images:
            issues.append(f"⚠️ 配图数 {len(image_paths)} 超过建议限制 {self.max_images}")

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
            "平台：抖音。发布前必须满足所有硬性条件：\n"
            f"- 正文不得少于 2000 字（硬性要求，低于直接打回重写）\n"
            f"- 配图不得少于 3 张（硬性要求，低于直接打回重写）\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 禁止使用 emoji 表情包、特殊符号装饰（❌✅⚠️💥🔥等），内容要像真人写的，不要像 AI 批量生成\n"
            "- 口语化表达，节奏感强\n"
            "- 开头用 hook 吸引注意力\n"
            "- 分段清晰，自然分段，不要用符号装饰\n"
            "- 结尾引导互动（点赞、评论、关注）\n"
            f"- 最多 {self.max_tags} 个话题标签\n"
            f"- 最多 {self.max_images} 张配图\n"
            "- 所有配图必须是真实图片（文档截图/实拍图），不要全是 AI 生成的图\n"
        )
