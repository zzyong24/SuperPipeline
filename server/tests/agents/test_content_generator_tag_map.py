"""Tests for content_generator tag_map integration."""

import json
import pytest
from unittest.mock import AsyncMock

from src.agents.content_generator.agent import (
    _load_tag_map,
    _get_topic_key_and_strategy,
    ContentGeneratorAgent,
)
from src.agents.content_generator.schemas import ContentGenConfig


class TestLoadTagMap:
    def test_load_tag_map_returns_dict(self):
        tag_map = _load_tag_map()
        assert isinstance(tag_map, dict)
        assert "topic_tag_strategies" in tag_map
        assert "_default_strategy" in tag_map

    def test_tag_map_has_required_keys(self):
        tag_map = _load_tag_map()
        strategies = tag_map["topic_tag_strategies"]
        for key, strategy in strategies.items():
            assert "core_tags" in strategy
            assert "hot_tags" in strategy
            assert "audience_tags" in strategy
            assert "hashtag_style" in strategy


class TestGetTopicKeyAndStrategy:
    def test_exact_title_match(self):
        topic_key, strategy = _get_topic_key_and_strategy("AI编程工具对比", "深度横评")
        assert topic_key == "AI编程工具对比"
        assert "核心标签" in strategy
        assert "AI编程" in strategy

    def test_angle_keyword_match(self):
        topic_key, strategy = _get_topic_key_and_strategy("some unrelated title", "大模型应用技巧")
        assert topic_key == "大模型应用"
        assert "大模型" in strategy

    def test_partial_match(self):
        topic_key, strategy = _get_topic_key_and_strategy("最全的编程教程", "入门指南")
        assert topic_key == "编程教程"
        assert "Python" in strategy

    def test_unknown_topic_falls_back_to_default(self):
        topic_key, strategy = _get_topic_key_and_strategy("完全不相关的标题", "xyz123")
        assert topic_key == "通用内容"
        assert "干货分享" in strategy

    def test_strategy_string_format(self):
        _, strategy = _get_topic_key_and_strategy("工具测评", "对比")
        assert "核心标签（必选" in strategy
        assert "热点标签（可选" in strategy
        assert "受众标签" in strategy
        assert "Hashtag 格式" in strategy
        assert "5-8个" in strategy


class TestContentGeneratorTagIntegration:
    @pytest.mark.asyncio
    async def test_agent_injects_topic_key_and_tag_strategy(self):
        """Verify that agent.run() calls _get_topic_key_and_strategy and passes results to prompt."""
        mock_model = AsyncMock()
        mock_model.generate = AsyncMock(
            return_value=json.dumps({
                "title": "AI工具大测评",
                "body": "测试内容正文" * 100,
                "tags": ["AI编程", "效率神器"],
                "image_prompts": [],
            })
        )

        agent = ContentGeneratorAgent(model=mock_model)
        config = ContentGenConfig(platform="douyin", format="text")
        inputs = {
            "selected_topic": {"title": "AI编程工具对比", "angle": "横评对比"},
            "materials": [{"source": "https://example.com", "title": "Ref", "snippet": "data", "source_type": "web"}],
        }

        result = await agent.run(inputs, config)

        # Verify model.generate was called
        mock_model.generate.assert_called_once()
        call_args = mock_model.generate.call_args
        prompt = call_args[0][0]

        # Verify topic_key and tag_strategy appear in the prompt
        assert "AI编程工具对比" in prompt
        assert "核心标签" in prompt
        assert "热点标签" in prompt
        assert "Hashtag 格式" in prompt
        assert "contents" in result

    @pytest.mark.asyncio
    async def test_tag_strategy_unknown_topic_uses_default(self):
        """When topic doesn't match any known key, use default strategy."""
        mock_model = AsyncMock()
        mock_model.generate = AsyncMock(
            return_value=json.dumps({
                "title": "Test",
                "body": "Body",
                "tags": [],
                "image_prompts": [],
            })
        )

        agent = ContentGeneratorAgent(model=mock_model)
        config = ContentGenConfig(platform="xiaohongshu", format="image_text")
        inputs = {
            "selected_topic": {"title": "完全未知的话题标题", "angle": "xyz"},
            "materials": [],
        }

        await agent.run(inputs, config)

        call_args = mock_model.generate.call_args
        prompt = call_args[0][0]
        # Should use default strategy
        assert "通用内容" in prompt
        assert "干货分享" in prompt
