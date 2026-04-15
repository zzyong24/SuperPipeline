import pytest
from src.core.state import (
    UserBrief,
    Topic,
    Material,
    PlatformContent,
    ReviewResult,
    PipelineError,
    PipelineState,
)


def test_user_brief_creation():
    brief = UserBrief(topic="AI tools review", keywords=["AI", "coding"], platform_hints=["xiaohongshu"])
    assert brief.topic == "AI tools review"
    assert len(brief.keywords) == 2


def test_topic_creation():
    topic = Topic(title="Top 5 AI Coding Tools", angle="comparison", score=8.5)
    assert topic.title == "Top 5 AI Coding Tools"
    assert topic.score == 8.5


def test_platform_content_creation():
    content = PlatformContent(
        platform="xiaohongshu",
        title="AI编程工具大测评",
        body="正文内容...",
        tags=["AI", "编程"],
        image_paths=[],
    )
    assert content.platform == "xiaohongshu"
    assert len(content.tags) == 2


def test_review_result_creation():
    review = ReviewResult(
        platform="xiaohongshu",
        passed=True,
        score=8.0,
        issues=[],
        suggestions=["可以增加更多数据支撑"],
    )
    assert review.passed is True
    assert review.score == 8.0


def test_pipeline_error_creation():
    error = PipelineError(agent="topic_generator", error_type="model_error", message="API timeout")
    assert error.agent == "topic_generator"


def test_pipeline_state_is_typed_dict():
    """PipelineState should be a TypedDict for LangGraph compatibility."""
    assert hasattr(PipelineState, "__annotations__")
    assert "run_id" in PipelineState.__annotations__
    assert "user_brief" in PipelineState.__annotations__
    assert "stage" in PipelineState.__annotations__
