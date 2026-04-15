import pytest
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.core.registry import AgentRegistry, register_agent


class DummyConfig(BaseModel):
    param: str = "default"


class DummyAgent(BaseAgent):
    name = "dummy"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = DummyConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        return {"topics": [{"title": f"Topic about {inputs['user_brief']['topic']}"}]}


def test_register_and_get_agent():
    registry = AgentRegistry()
    registry.register(DummyAgent)
    agent = registry.get("dummy")
    assert isinstance(agent, DummyAgent)


def test_get_unregistered_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(KeyError, match="Agent 'nonexistent' not registered"):
        registry.get("nonexistent")


def test_register_agent_decorator():
    registry = AgentRegistry()
    decorator = register_agent(registry)

    @decorator
    class DecoratedAgent(BaseAgent):
        name = "decorated"
        consumes = ["user_brief"]
        produces = ["topics"]
        config_schema = DummyConfig

        async def run(self, inputs: dict, config: BaseModel) -> dict:
            return {"topics": []}

    agent = registry.get("decorated")
    assert isinstance(agent, DecoratedAgent)


def test_list_agents():
    registry = AgentRegistry()
    registry.register(DummyAgent)
    agents = registry.list_agents()
    assert len(agents) == 1
    assert agents[0]["name"] == "dummy"
    assert agents[0]["consumes"] == ["user_brief"]
    assert agents[0]["produces"] == ["topics"]


@pytest.mark.asyncio
async def test_agent_validate_inputs_pass():
    agent = DummyAgent()
    state = {"user_brief": {"topic": "AI"}}
    assert agent.validate_inputs(state) is True


@pytest.mark.asyncio
async def test_agent_validate_inputs_fail():
    agent = DummyAgent()
    state = {"something_else": "data"}
    assert agent.validate_inputs(state) is False


@pytest.mark.asyncio
async def test_agent_validate_outputs_pass():
    agent = DummyAgent()
    outputs = {"topics": [{"title": "Test"}]}
    assert agent.validate_outputs(outputs) is True


@pytest.mark.asyncio
async def test_agent_validate_outputs_fail():
    agent = DummyAgent()
    outputs = {"wrong_key": "data"}
    assert agent.validate_outputs(outputs) is False
