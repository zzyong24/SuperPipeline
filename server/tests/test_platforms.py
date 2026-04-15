import pytest
from src.platforms.base import BasePlatform, get_platform
from src.platforms.xiaohongshu import XiaohongshuPlatform
from src.platforms.x_twitter import XPlatform


def test_xiaohongshu_max_text_length():
    p = XiaohongshuPlatform()
    assert p.name == "xiaohongshu"
    assert p.max_text_length == 1000


def test_xiaohongshu_validate_pass():
    p = XiaohongshuPlatform()
    issues = p.validate({"body": "一篇正常的小红书笔记内容，至少二十个字哦哦哦哦哦哦", "tags": ["#测试"]})
    assert len(issues) == 0


def test_xiaohongshu_validate_too_long():
    p = XiaohongshuPlatform()
    issues = p.validate({"body": "x" * 1001, "tags": []})
    assert any("字数" in i or "length" in i.lower() for i in issues)


def test_xiaohongshu_format_adds_tags():
    p = XiaohongshuPlatform()
    result = p.format_content("正文内容", tags=["AI", "工具"])
    assert "#AI" in result
    assert "#工具" in result


def test_x_platform_max_length():
    p = XPlatform()
    assert p.name == "x"
    assert p.max_text_length == 280


def test_x_validate_too_long():
    p = XPlatform()
    issues = p.validate({"body": "x" * 281, "tags": []})
    assert len(issues) > 0


def test_get_platform_by_name():
    p = get_platform("xiaohongshu")
    assert isinstance(p, XiaohongshuPlatform)
    p2 = get_platform("x")
    assert isinstance(p2, XPlatform)


def test_get_platform_unknown():
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform("tiktok")
