"""Test that orchestrator saves snapshots during execution."""

import pytest
from pydantic import BaseModel

from src.core.orchestrator import Orchestrator
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, StageConfig, UserBrief
from src.storage.state_store import StateStore


class DummyConfig(BaseModel):
    value: str = "default"


class DummyAgent:
    name = "dummy"
    consumes = ["user_brief"]
    produces = ["analysis"]
    config_schema = DummyConfig

    def __init__(self, model=None):
        self.model = model

    def validate_inputs(self, state):
        return all(k in state and state[k] is not None for k in self.consumes)

    def validate_outputs(self, outputs):
        return all(k in outputs for k in self.produces)

    async def run(self, inputs, config):
        return {"analysis": {"data": "hello"}}


class FailingAgent:
    name = "failing"
    consumes = ["user_brief"]
    produces = ["result"]
    config_schema = DummyConfig

    def __init__(self, model=None):
        self.model = model

    def validate_inputs(self, state):
        return all(k in state and state[k] is not None for k in self.consumes)

    def validate_outputs(self, outputs):
        return True

    async def run(self, inputs, config):
        raise ValueError("intentional failure")


@pytest.fixture
async def store(tmp_path):
    s = StateStore(str(tmp_path / "test.db"))
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_snapshot_saved_on_success(store):
    registry = AgentRegistry()
    registry.register(DummyAgent)

    orchestrator = Orchestrator(registry, state_store=store)

    config = PipelineConfig(
        name="test", stages=[StageConfig(agent="dummy")]
    )
    brief = UserBrief(topic="test")

    result = await orchestrator.run(config, brief, run_id="snap_test_1")

    snapshots = await store.list_snapshots("snap_test_1")
    assert len(snapshots) == 1
    assert snapshots[0]["agent"] == "dummy"
    assert snapshots[0]["status"] == "completed"
    assert snapshots[0]["outputs"]["analysis"]["data"] == "hello"
    assert snapshots[0]["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_snapshot_saved_on_failure(store):
    registry = AgentRegistry()
    registry.register(FailingAgent)

    orchestrator = Orchestrator(registry, state_store=store)

    config = PipelineConfig(
        name="test", stages=[StageConfig(agent="failing", on_error="halt")]
    )
    brief = UserBrief(topic="test")

    result = await orchestrator.run(config, brief, run_id="snap_fail_1")
    assert result["stage"] == "failed"

    snapshots = await store.list_snapshots("snap_fail_1")
    assert len(snapshots) == 1
    assert snapshots[0]["agent"] == "failing"
    assert snapshots[0]["status"] == "failed"
    assert "intentional failure" in snapshots[0]["error"]


@pytest.mark.asyncio
async def test_no_store_no_crash():
    """Orchestrator without state_store should still work (no snapshots)."""
    registry = AgentRegistry()
    registry.register(DummyAgent)

    orchestrator = Orchestrator(registry)  # no state_store

    config = PipelineConfig(
        name="test", stages=[StageConfig(agent="dummy")]
    )
    brief = UserBrief(topic="test")

    result = await orchestrator.run(config, brief, run_id="no_store_1")
    assert result["analysis"]["data"] == "hello"
