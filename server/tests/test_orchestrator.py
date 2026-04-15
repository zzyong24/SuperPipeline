import pytest
from pydantic import BaseModel
from src.core.orchestrator import Orchestrator
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, StageConfig, UserBrief
from src.agents.base import BaseAgent


class EchoConfig(BaseModel):
    prefix: str = "echo"


class EchoTopicAgent(BaseAgent):
    name = "echo_topic"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = EchoConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        brief = UserBrief.model_validate(inputs["user_brief"])
        return {"topics": [{"title": f"{config.prefix}: {brief.topic}", "angle": "", "score": 9.0}]}


class EchoContentAgent(BaseAgent):
    name = "echo_content"
    consumes = ["topics"]
    produces = ["contents"]
    config_schema = EchoConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        title = inputs["topics"][0]["title"]
        return {
            "contents": {
                "test_platform": {
                    "platform": "test_platform",
                    "title": title,
                    "body": f"Content about: {title}",
                    "tags": [],
                    "image_paths": [],
                }
            }
        }


@pytest.fixture
def registry():
    reg = AgentRegistry()
    reg.register(EchoTopicAgent)
    reg.register(EchoContentAgent)
    return reg


@pytest.fixture
def pipeline_config():
    return PipelineConfig(
        name="test",
        description="test pipeline",
        platforms=["test_platform"],
        stages=[
            StageConfig(agent="echo_topic", config={"prefix": "TEST"}),
            StageConfig(agent="echo_content", config={"prefix": "GEN"}),
        ],
    )


@pytest.mark.asyncio
async def test_orchestrator_builds_and_runs(registry, pipeline_config):
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=pipeline_config,
        user_brief=UserBrief(topic="AI tools", keywords=["AI"]),
    )
    assert result["stage"] == "completed"
    assert len(result["topics"]) == 1
    assert result["topics"][0]["title"] == "TEST: AI tools"
    assert "test_platform" in result["contents"]
    assert result["contents"]["test_platform"]["body"] == "Content about: TEST: AI tools"


@pytest.mark.asyncio
async def test_orchestrator_returns_run_id(registry, pipeline_config):
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=pipeline_config,
        user_brief=UserBrief(topic="test"),
    )
    assert "run_id" in result
    assert len(result["run_id"]) > 0


@pytest.mark.asyncio
async def test_orchestrator_handles_agent_error(registry):
    """If an agent raises, error is captured in state.errors."""

    class FailingAgent(BaseAgent):
        name = "failing_agent"
        consumes = ["user_brief"]
        produces = ["topics"]
        config_schema = EchoConfig

        async def run(self, inputs, config):
            raise RuntimeError("Intentional failure")

    registry.register(FailingAgent)

    config = PipelineConfig(
        name="fail_test",
        stages=[StageConfig(agent="failing_agent", config={})],
    )
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=config,
        user_brief=UserBrief(topic="test"),
    )
    assert result["stage"] == "failed"
    assert len(result["errors"]) > 0
    assert result["errors"][0]["agent"] == "failing_agent"
