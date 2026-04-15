"""Test prompt_override support in agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from src.agents.base import BaseAgent


class TestConfig(BaseModel):
    value: str = "default"


class TestAgent(BaseAgent):
    name = "test_agent"
    consumes = ["input"]
    produces = ["output"]
    config_schema = TestConfig

    async def run(self, inputs, config):
        prompt = self.get_prompt("test.j2", config, key="value")
        return {"output": prompt}


def test_get_prompt_without_override():
    """Without override, falls through to load_prompt."""
    agent = TestAgent()
    config = TestConfig()
    # This will fail because test.j2 doesn't exist, but it proves
    # the code path goes to load_prompt
    with pytest.raises(Exception):
        agent.get_prompt("nonexistent.j2", config, key="val")


def test_get_prompt_with_override():
    """With _prompt_override, returns override directly."""
    agent = TestAgent()
    config = TestConfig()
    object.__setattr__(config, '_prompt_override', 'You are a custom agent')
    result = agent.get_prompt("generate.j2", config, key="val")
    assert result == "You are a custom agent"


def test_get_prompt_override_empty_string():
    """Empty string override still falls through to template."""
    agent = TestAgent()
    config = TestConfig()
    object.__setattr__(config, '_prompt_override', '')
    # Empty string is falsy, should fall through to load_prompt
    with pytest.raises(Exception):
        agent.get_prompt("nonexistent.j2", config)
