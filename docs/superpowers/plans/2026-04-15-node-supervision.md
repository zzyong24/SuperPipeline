# Node Supervision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade SuperPipeline from "configure and run" to "observe, edit, and rerun each node" — a full node-level supervision system. Primary use case: Claude Code agent debugs and optimizes content pipelines via CLI, step by step.

**Spec:** `docs/superpowers/specs/2026-04-15-node-supervision-design.md`

**Architecture:** Each pipeline node execution saves a complete snapshot (inputs, outputs, config, timing) to SQLite. Snapshots support versioning — reruns create new versions. Cascade rerun reads inputs from a stage's snapshot and re-executes all downstream stages. CLI and API expose full CRUD for snapshots.

**Working directory:** All commands assume `cd server/` and use `.venv/bin/python -m pytest`.

---

## Task 1: stage_snapshots table + CRUD in StateStore

**Files:**
- Modify: `server/src/storage/state_store.py`
- Create: `server/tests/test_state_store_snapshots.py`

- [ ] **Step 1: Write tests for snapshot CRUD**

```bash
# Verify: test file exists and tests fail (no implementation yet)
cd server && .venv/bin/python -m pytest tests/test_state_store_snapshots.py -v
```

Create `server/tests/test_state_store_snapshots.py`:

```python
"""Tests for stage_snapshots CRUD in StateStore."""

from __future__ import annotations

import pytest
from src.storage.state_store import StateStore


@pytest.fixture
async def store(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = StateStore(db_path)
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_save_and_get_snapshot(store: StateStore):
    """save_snapshot + get_snapshot round-trip."""
    await store.save_snapshot(
        run_id="run1",
        agent="topic_generator",
        version=1,
        status="completed",
        config={"model": "MiniMax-M2.5", "params": {"count": 5}},
        inputs={"user_brief": {"topic": "AI"}},
        outputs={"topics": [{"title": "AI trends"}]},
        error=None,
        duration_ms=1200,
    )
    snap = await store.get_snapshot("run1", "topic_generator")
    assert snap is not None
    assert snap["agent"] == "topic_generator"
    assert snap["version"] == 1
    assert snap["status"] == "completed"
    assert snap["config"]["model"] == "MiniMax-M2.5"
    assert snap["inputs"]["user_brief"]["topic"] == "AI"
    assert snap["outputs"]["topics"][0]["title"] == "AI trends"
    assert snap["error"] is None
    assert snap["duration_ms"] == 1200


@pytest.mark.asyncio
async def test_get_snapshot_specific_version(store: StateStore):
    """get_snapshot with explicit version."""
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={}, inputs={}, outputs={"v": 1}, error=None, duration_ms=100,
    )
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=2, status="completed",
        config={}, inputs={}, outputs={"v": 2}, error=None, duration_ms=200,
    )
    # Latest (no version)
    snap = await store.get_snapshot("run1", "topic_generator")
    assert snap["version"] == 2
    assert snap["outputs"]["v"] == 2

    # Specific version
    snap_v1 = await store.get_snapshot("run1", "topic_generator", version=1)
    assert snap_v1["version"] == 1
    assert snap_v1["outputs"]["v"] == 1


@pytest.mark.asyncio
async def test_list_snapshots(store: StateStore):
    """list_snapshots returns latest version per agent."""
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={}, inputs={}, outputs={"v": 1}, error=None, duration_ms=100,
    )
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=2, status="completed",
        config={}, inputs={}, outputs={"v": 2}, error=None, duration_ms=150,
    )
    await store.save_snapshot(
        run_id="run1", agent="content_generator", version=1, status="failed",
        config={}, inputs={}, outputs=None, error="timeout", duration_ms=5000,
    )

    snapshots = await store.list_snapshots("run1")
    assert len(snapshots) == 2
    agents = {s["agent"] for s in snapshots}
    assert agents == {"topic_generator", "content_generator"}
    # topic_generator should be version 2 (latest)
    tg = next(s for s in snapshots if s["agent"] == "topic_generator")
    assert tg["version"] == 2


@pytest.mark.asyncio
async def test_list_snapshot_history(store: StateStore):
    """list_snapshot_history returns all versions for one agent."""
    for v in range(1, 4):
        await store.save_snapshot(
            run_id="run1", agent="reviewer", version=v, status="completed",
            config={"attempt": v}, inputs={}, outputs={"v": v},
            error=None, duration_ms=v * 100,
        )
    history = await store.list_snapshot_history("run1", "reviewer")
    assert len(history) == 3
    assert [h["version"] for h in history] == [1, 2, 3]


@pytest.mark.asyncio
async def test_update_snapshot_outputs(store: StateStore):
    """update_snapshot_outputs creates a new version with edited outputs."""
    await store.save_snapshot(
        run_id="run1", agent="content_generator", version=1, status="completed",
        config={}, inputs={}, outputs={"title": "old"}, error=None, duration_ms=100,
    )
    await store.update_snapshot_outputs(
        run_id="run1", agent="content_generator", version=1,
        outputs={"title": "edited"},
    )
    snap = await store.get_snapshot("run1", "content_generator", version=1)
    assert snap["outputs"]["title"] == "edited"


@pytest.mark.asyncio
async def test_get_next_version(store: StateStore):
    """get_next_version returns max(version)+1."""
    # No snapshots yet
    v = await store.get_next_version("run1", "topic_generator")
    assert v == 1

    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={}, inputs={}, outputs={}, error=None, duration_ms=100,
    )
    v = await store.get_next_version("run1", "topic_generator")
    assert v == 2

    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=2, status="completed",
        config={}, inputs={}, outputs={}, error=None, duration_ms=100,
    )
    v = await store.get_next_version("run1", "topic_generator")
    assert v == 3


@pytest.mark.asyncio
async def test_get_snapshot_not_found(store: StateStore):
    """get_snapshot returns None for nonexistent snapshot."""
    snap = await store.get_snapshot("nonexistent", "fake_agent")
    assert snap is None


@pytest.mark.asyncio
async def test_save_snapshot_failed_with_error(store: StateStore):
    """Failed snapshot stores error, outputs is None."""
    await store.save_snapshot(
        run_id="run1", agent="reviewer", version=1, status="failed",
        config={"min_score": 7.0}, inputs={"contents": {}},
        outputs=None, error="Model returned invalid JSON",
        duration_ms=3500,
    )
    snap = await store.get_snapshot("run1", "reviewer")
    assert snap["status"] == "failed"
    assert snap["outputs"] is None
    assert snap["error"] == "Model returned invalid JSON"
```

- [ ] **Step 2: Add stage_snapshots table to initialize() and implement CRUD methods**

Modify `server/src/storage/state_store.py` — add to `initialize()` after existing tables:

```python
            CREATE TABLE IF NOT EXISTS stage_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                agent TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL DEFAULT '{}',
                inputs_json TEXT NOT NULL DEFAULT '{}',
                outputs_json TEXT,
                error TEXT,
                duration_ms INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(run_id, agent, version)
            );
```

Add these methods to `StateStore` class (after `update_content`):

```python
    # ── Stage Snapshots ───────────────────────────────────────────────

    async def save_snapshot(
        self,
        run_id: str,
        agent: str,
        version: int,
        status: str,
        config: dict,
        inputs: dict,
        outputs: dict | None,
        error: str | None,
        duration_ms: int | None,
    ) -> None:
        await self._db.execute(
            """INSERT INTO stage_snapshots
               (run_id, agent, version, status, config_json, inputs_json, outputs_json, error, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, agent, version, status,
                json.dumps(config, ensure_ascii=False),
                json.dumps(inputs, ensure_ascii=False),
                json.dumps(outputs, ensure_ascii=False) if outputs is not None else None,
                error, duration_ms, self._now(),
            ),
        )
        await self._db.commit()

    async def get_snapshot(self, run_id: str, agent: str, version: int | None = None) -> dict | None:
        if version is not None:
            cursor = await self._db.execute(
                "SELECT * FROM stage_snapshots WHERE run_id = ? AND agent = ? AND version = ?",
                (run_id, agent, version),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM stage_snapshots WHERE run_id = ? AND agent = ? ORDER BY version DESC LIMIT 1",
                (run_id, agent),
            )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._parse_snapshot_row(row)

    async def list_snapshots(self, run_id: str) -> list[dict]:
        cursor = await self._db.execute(
            """SELECT s.* FROM stage_snapshots s
               INNER JOIN (
                   SELECT run_id, agent, MAX(version) as max_v
                   FROM stage_snapshots WHERE run_id = ?
                   GROUP BY run_id, agent
               ) latest ON s.run_id = latest.run_id AND s.agent = latest.agent AND s.version = latest.max_v
               ORDER BY s.id""",
            (run_id,),
        )
        rows = await cursor.fetchall()
        return [self._parse_snapshot_row(r) for r in rows]

    async def list_snapshot_history(self, run_id: str, agent: str) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM stage_snapshots WHERE run_id = ? AND agent = ? ORDER BY version ASC",
            (run_id, agent),
        )
        rows = await cursor.fetchall()
        return [self._parse_snapshot_row(r) for r in rows]

    async def update_snapshot_outputs(self, run_id: str, agent: str, version: int, outputs: dict) -> None:
        await self._db.execute(
            "UPDATE stage_snapshots SET outputs_json = ? WHERE run_id = ? AND agent = ? AND version = ?",
            (json.dumps(outputs, ensure_ascii=False), run_id, agent, version),
        )
        await self._db.commit()

    async def get_next_version(self, run_id: str, agent: str) -> int:
        cursor = await self._db.execute(
            "SELECT MAX(version) FROM stage_snapshots WHERE run_id = ? AND agent = ?",
            (run_id, agent),
        )
        row = await cursor.fetchone()
        max_v = row[0] if row and row[0] is not None else 0
        return max_v + 1

    def _parse_snapshot_row(self, row) -> dict:
        d = dict(row)
        d["config"] = json.loads(d.pop("config_json"))
        d["inputs"] = json.loads(d.pop("inputs_json"))
        outputs_raw = d.pop("outputs_json")
        d["outputs"] = json.loads(outputs_raw) if outputs_raw is not None else None
        return d
```

- [ ] **Step 3: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_state_store_snapshots.py -v
```

- [ ] **Step 4: Commit**

```
feat(storage): 新增 stage_snapshots 表和 CRUD 方法

支持快照保存/查询/版本历史/输出编辑，为节点监督提供数据基础。
```

---

## Task 2: StageConfig model extension

**Files:**
- Modify: `server/src/core/state.py`
- Create: `server/tests/test_state_models.py`

- [ ] **Step 1: Write tests for new StageConfig fields**

Create `server/tests/test_state_models.py`:

```python
"""Tests for StageConfig model extensions."""

from __future__ import annotations

import pytest
from src.core.state import StageConfig


def test_stage_config_defaults():
    """New fields default to None."""
    cfg = StageConfig(agent="topic_generator")
    assert cfg.model_override is None
    assert cfg.model_provider is None
    assert cfg.prompt_override is None


def test_stage_config_with_overrides():
    """New fields accept values."""
    cfg = StageConfig(
        agent="topic_generator",
        config={"count": 3},
        model_override="MiniMax-M2.7",
        model_provider="minimax",
        prompt_override="You are a topic expert.",
    )
    assert cfg.model_override == "MiniMax-M2.7"
    assert cfg.model_provider == "minimax"
    assert cfg.prompt_override == "You are a topic expert."
    assert cfg.config == {"count": 3}


def test_stage_config_backward_compatible():
    """Existing configs without new fields still work."""
    cfg = StageConfig.model_validate({
        "agent": "reviewer",
        "config": {"min_score": 7.0},
        "on_error": "skip",
        "retry_count": 2,
    })
    assert cfg.agent == "reviewer"
    assert cfg.on_error == "skip"
    assert cfg.model_override is None


def test_stage_config_model_copy_preserves_overrides():
    """model_copy with update preserves override fields."""
    original = StageConfig(
        agent="content_generator",
        model_override="MiniMax-M2.7",
        prompt_override="Custom prompt",
    )
    copied = original.model_copy(update={"config": {"style": "deep"}})
    assert copied.model_override == "MiniMax-M2.7"
    assert copied.prompt_override == "Custom prompt"
    assert copied.config == {"style": "deep"}
```

```bash
cd server && .venv/bin/python -m pytest tests/test_state_models.py -v
```

- [ ] **Step 2: Add new fields to StageConfig**

Modify `server/src/core/state.py` — replace the `StageConfig` class:

```python
class StageConfig(BaseModel):
    """One stage in a pipeline YAML."""

    agent: str
    config: dict = Field(default_factory=dict)
    on_error: str = Field(default="halt", description="skip | retry | halt")
    retry_count: int = Field(default=1)
    # Node supervision overrides
    model_override: str | None = Field(default=None, description="Override model name for this stage")
    model_provider: str | None = Field(default=None, description="Override model provider for this stage")
    prompt_override: str | None = Field(default=None, description="Inline prompt override (skip Jinja2 template)")
```

- [ ] **Step 3: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_state_models.py -v
```

- [ ] **Step 4: Commit**

```
feat(state): StageConfig 新增 model_override/prompt_override 字段

支持运行时动态覆盖节点的模型和提示词。
```

---

## Task 3: Orchestrator snapshot integration

**Files:**
- Modify: `server/src/core/orchestrator.py`
- Create: `server/tests/test_orchestrator_snapshots.py`

**Depends on:** Task 1, Task 2

- [ ] **Step 1: Write tests for orchestrator snapshot behavior**

Create `server/tests/test_orchestrator_snapshots.py`:

```python
"""Tests for orchestrator snapshot integration."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.orchestrator import Orchestrator
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, StageConfig, UserBrief
from src.storage.state_store import StateStore
from src.agents.base import BaseAgent
from pydantic import BaseModel


class DummyConfig(BaseModel):
    value: str = "default"


class DummyAgent(BaseAgent):
    name = "dummy_agent"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = DummyConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        return {"topics": [{"title": "test topic"}]}


class FailingAgent(BaseAgent):
    name = "failing_agent"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = DummyConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        raise ValueError("intentional failure")


@pytest.fixture
async def store(tmp_path):
    s = StateStore(str(tmp_path / "test.db"))
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def registry():
    reg = AgentRegistry()
    return reg


@pytest.mark.asyncio
async def test_wrap_agent_saves_snapshot_on_success(store: StateStore, registry: AgentRegistry):
    """_wrap_agent saves a completed snapshot after successful execution."""
    registry.register(DummyAgent)
    orchestrator = Orchestrator(registry)

    agent = registry.get("dummy_agent")
    stage_config = StageConfig(agent="dummy_agent", config={"value": "test"})
    node_fn = orchestrator._wrap_agent(agent, stage_config, state_store=store, run_id="run1")

    state = {
        "run_id": "run1",
        "user_brief": {"topic": "AI", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "errors": [],
    }
    result = await node_fn(state)

    assert result["topics"] == [{"title": "test topic"}]

    # Check snapshot was saved
    snap = await store.get_snapshot("run1", "dummy_agent")
    assert snap is not None
    assert snap["status"] == "completed"
    assert snap["inputs"]["user_brief"]["topic"] == "AI"
    assert snap["outputs"]["topics"][0]["title"] == "test topic"
    assert snap["duration_ms"] >= 0
    assert snap["error"] is None


@pytest.mark.asyncio
async def test_wrap_agent_saves_snapshot_on_failure(store: StateStore, registry: AgentRegistry):
    """_wrap_agent saves a failed snapshot after agent error."""
    registry.register(FailingAgent)
    orchestrator = Orchestrator(registry)

    agent = registry.get("failing_agent")
    stage_config = StageConfig(agent="failing_agent", config={}, on_error="halt", retry_count=1)
    node_fn = orchestrator._wrap_agent(agent, stage_config, state_store=store, run_id="run1")

    state = {
        "run_id": "run1",
        "user_brief": {"topic": "test", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "errors": [],
    }
    result = await node_fn(state)

    assert result["stage"] == "failed"

    snap = await store.get_snapshot("run1", "failing_agent")
    assert snap is not None
    assert snap["status"] == "failed"
    assert "intentional failure" in snap["error"]
    assert snap["duration_ms"] >= 0


@pytest.mark.asyncio
async def test_wrap_agent_without_store_still_works(registry: AgentRegistry):
    """_wrap_agent works without state_store (backward compatible)."""
    registry.register(DummyAgent)
    orchestrator = Orchestrator(registry)

    agent = registry.get("dummy_agent")
    stage_config = StageConfig(agent="dummy_agent")
    node_fn = orchestrator._wrap_agent(agent, stage_config)

    state = {
        "run_id": "run1",
        "user_brief": {"topic": "AI", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "errors": [],
    }
    result = await node_fn(state)
    assert result["topics"] == [{"title": "test topic"}]


@pytest.mark.asyncio
async def test_wrap_agent_increments_version(store: StateStore, registry: AgentRegistry):
    """Second run of same agent increments snapshot version."""
    registry.register(DummyAgent)
    orchestrator = Orchestrator(registry)

    # Pre-seed a version 1 snapshot
    await store.save_snapshot(
        run_id="run1", agent="dummy_agent", version=1, status="completed",
        config={}, inputs={}, outputs={"old": True}, error=None, duration_ms=100,
    )

    agent = registry.get("dummy_agent")
    stage_config = StageConfig(agent="dummy_agent")
    node_fn = orchestrator._wrap_agent(agent, stage_config, state_store=store, run_id="run1")

    state = {
        "run_id": "run1",
        "user_brief": {"topic": "AI", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "errors": [],
    }
    await node_fn(state)

    snap = await store.get_snapshot("run1", "dummy_agent")
    assert snap["version"] == 2
    assert snap["outputs"]["topics"][0]["title"] == "test topic"


@pytest.mark.asyncio
async def test_prompt_override_passed_to_agent(store: StateStore, registry: AgentRegistry):
    """prompt_override in StageConfig is passed to agent via config._prompt_override."""
    received_config = {}

    class SpyAgent(BaseAgent):
        name = "spy_agent"
        consumes = ["user_brief"]
        produces = ["topics"]
        config_schema = DummyConfig

        async def run(self, inputs: dict, config: BaseModel) -> dict:
            received_config["prompt_override"] = getattr(config, "_prompt_override", None)
            return {"topics": []}

    registry.register(SpyAgent)
    orchestrator = Orchestrator(registry)

    agent = registry.get("spy_agent")
    stage_config = StageConfig(
        agent="spy_agent",
        prompt_override="You are a custom prompt.",
    )
    node_fn = orchestrator._wrap_agent(agent, stage_config, state_store=store, run_id="run1")

    state = {
        "run_id": "run1",
        "user_brief": {"topic": "test", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "errors": [],
    }
    await node_fn(state)

    assert received_config["prompt_override"] == "You are a custom prompt."
```

```bash
cd server && .venv/bin/python -m pytest tests/test_orchestrator_snapshots.py -v
```

- [ ] **Step 2: Modify `_wrap_agent()` to save snapshots**

Replace the entire `server/src/core/orchestrator.py`:

```python
"""Orchestrator — dynamically builds LangGraph pipelines from YAML config."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.base import BaseAgent
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, PipelineState, StageConfig, UserBrief


class Orchestrator:
    """Reads pipeline config, assembles a LangGraph StateGraph, and runs it."""

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self.checkpointer = MemorySaver()

    def _wrap_agent(
        self,
        agent: BaseAgent,
        stage_config: StageConfig,
        state_store=None,
        run_id: str | None = None,
    ):
        """Wrap an agent into a LangGraph node function with retry, on_error, and snapshot support."""
        config = agent.config_schema.model_validate(stage_config.config)
        on_error = stage_config.on_error
        retry_count = stage_config.retry_count

        # Inject prompt_override into config if present
        if stage_config.prompt_override:
            object.__setattr__(config, "_prompt_override", stage_config.prompt_override)

        # Build effective config dict for snapshot storage
        effective_config = {
            "model": stage_config.model_override or "default",
            "model_provider": stage_config.model_provider,
            "prompt_override": stage_config.prompt_override,
            "params": stage_config.config,
        }

        async def node_fn(state: PipelineState) -> dict:
            updates: dict[str, Any] = {"stage": agent.name}
            current_run_id = run_id or state.get("run_id", "unknown")

            if not agent.validate_inputs(state):
                error = {
                    "agent": agent.name,
                    "error_type": "validation_error",
                    "message": f"Missing required inputs: {agent.consumes}",
                    "recoverable": False,
                }
                errors = list(state.get("errors", []))
                errors.append(error)
                updates["errors"] = errors

                # Save failed snapshot for validation errors
                if state_store and current_run_id:
                    version = await state_store.get_next_version(current_run_id, agent.name)
                    await state_store.save_snapshot(
                        run_id=current_run_id, agent=agent.name, version=version,
                        status="failed", config=effective_config,
                        inputs={}, outputs=None,
                        error=error["message"], duration_ms=0,
                    )

                if on_error == "skip":
                    return updates
                updates["stage"] = "failed"
                return updates

            inputs = {key: state[key] for key in agent.consumes if key in state}

            # Determine version for snapshot
            version = 1
            if state_store and current_run_id:
                version = await state_store.get_next_version(current_run_id, agent.name)
                # Save "running" snapshot before execution
                await state_store.save_snapshot(
                    run_id=current_run_id, agent=agent.name, version=version,
                    status="running", config=effective_config,
                    inputs=inputs, outputs=None, error=None, duration_ms=None,
                )

            start_time = time.monotonic()
            last_exception = None
            for attempt in range(max(1, retry_count)):
                try:
                    outputs = await agent.run(inputs, config)
                    duration_ms = int((time.monotonic() - start_time) * 1000)

                    if not agent.validate_outputs(outputs):
                        raise ValueError(f"Agent did not produce required outputs: {agent.produces}")

                    for key, value in outputs.items():
                        if isinstance(value, dict) and isinstance(state.get(key), dict):
                            merged = dict(state[key])
                            merged.update(value)
                            updates[key] = merged
                        else:
                            updates[key] = value

                    # Save completed snapshot
                    if state_store and current_run_id:
                        await state_store._db.execute(
                            """UPDATE stage_snapshots
                               SET status = ?, outputs_json = ?, duration_ms = ?
                               WHERE run_id = ? AND agent = ? AND version = ?""",
                            (
                                "completed",
                                __import__("json").dumps(outputs, ensure_ascii=False),
                                duration_ms,
                                current_run_id, agent.name, version,
                            ),
                        )
                        await state_store._db.commit()

                    return updates
                except Exception as e:
                    last_exception = e
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))

            duration_ms = int((time.monotonic() - start_time) * 1000)

            error = {
                "agent": agent.name,
                "error_type": type(last_exception).__name__,
                "message": str(last_exception),
                "recoverable": on_error != "halt",
            }
            errors = list(state.get("errors", []))
            errors.append(error)
            updates["errors"] = errors

            # Save failed snapshot
            if state_store and current_run_id:
                await state_store._db.execute(
                    """UPDATE stage_snapshots
                       SET status = ?, error = ?, duration_ms = ?
                       WHERE run_id = ? AND agent = ? AND version = ?""",
                    ("failed", str(last_exception), duration_ms, current_run_id, agent.name, version),
                )
                await state_store._db.commit()

            if on_error == "skip":
                return updates
            else:
                updates["stage"] = "failed"

            return updates

        return node_fn

    def build_graph(
        self,
        pipeline_config: PipelineConfig,
        stage_overrides: dict[str, dict] | None = None,
        state_store=None,
        run_id: str | None = None,
    ) -> StateGraph:
        """Build a LangGraph StateGraph from pipeline config."""
        graph = StateGraph(PipelineState)

        stages = pipeline_config.stages
        if not stages:
            raise ValueError("Pipeline has no stages")

        for stage in stages:
            effective_stage = stage
            if stage_overrides and stage.agent in stage_overrides:
                merged_config = {**stage.config, **stage_overrides[stage.agent]}
                effective_stage = stage.model_copy(update={"config": merged_config})
            agent = self.registry.get(stage.agent)
            graph.add_node(
                stage.agent,
                self._wrap_agent(agent, effective_stage, state_store=state_store, run_id=run_id),
            )

        graph.add_edge(START, stages[0].agent)
        for i in range(len(stages) - 1):
            current = stages[i].agent
            next_stage = stages[i + 1].agent
            graph.add_conditional_edges(
                current,
                lambda state, _next=next_stage: _next if state.get("stage") != "failed" else END,
            )
        graph.add_edge(stages[-1].agent, END)

        return graph

    async def run(
        self,
        pipeline_config: PipelineConfig,
        user_brief: UserBrief,
        run_id: str | None = None,
        stage_overrides: dict[str, dict] | None = None,
        state_store=None,
    ) -> dict:
        """Build and execute a pipeline."""
        run_id = run_id or uuid.uuid4().hex[:12]
        graph = self.build_graph(
            pipeline_config,
            stage_overrides=stage_overrides,
            state_store=state_store,
            run_id=run_id,
        )
        compiled = graph.compile(checkpointer=self.checkpointer)

        initial_state: dict[str, Any] = {
            "run_id": run_id,
            "pipeline_name": pipeline_config.name,
            "user_brief": user_brief.model_dump(),
            "topics": [],
            "materials": [],
            "contents": {},
            "reviews": {},
            "analysis": {},
            "stage": "starting",
            "errors": [],
            "metadata": {},
        }

        config = {"configurable": {"thread_id": run_id}}
        result = await compiled.ainvoke(initial_state, config=config)

        if result.get("stage") != "failed":
            result["stage"] = "completed"

        return result
```

- [ ] **Step 3: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_orchestrator_snapshots.py -v
```

- [ ] **Step 4: Commit**

```
feat(orchestrator): _wrap_agent 自动保存节点快照

每个节点执行前后保存完整快照到 stage_snapshots 表，支持 prompt_override 注入。
```

---

## Task 4: BaseAgent prompt_override support

**Files:**
- Modify: `server/src/agents/base.py`
- Modify: `server/src/agents/topic_generator/agent.py`
- Modify: `server/src/agents/material_collector/agent.py`
- Modify: `server/src/agents/content_generator/agent.py`
- Modify: `server/src/agents/reviewer/agent.py`
- Modify: `server/src/agents/analyst/agent.py`
- Create: `server/tests/test_agent_prompt_override.py`

**Depends on:** Task 3

- [ ] **Step 1: Write tests for prompt_override behavior**

Create `server/tests/test_agent_prompt_override.py`:

```python
"""Tests for BaseAgent prompt_override support."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.base import BaseAgent
from pydantic import BaseModel


class TestConfig(BaseModel):
    temperature: float = 0.5


class TestAgent(BaseAgent):
    name = "test_agent"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = TestConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        prompt = self.get_prompt(config, "generate.j2", topic="test")
        result = await self.model.generate(prompt, temperature=config.temperature)
        return {"topics": [result]}


@pytest.mark.asyncio
async def test_get_prompt_returns_override_when_set():
    """get_prompt returns _prompt_override when present on config."""
    agent = TestAgent(model=AsyncMock())
    config = TestConfig()
    object.__setattr__(config, "_prompt_override", "Custom prompt here")

    prompt = agent.get_prompt(config, "generate.j2", topic="ignored")
    assert prompt == "Custom prompt here"


@pytest.mark.asyncio
async def test_get_prompt_falls_back_to_template():
    """get_prompt falls back to load_prompt when no override."""
    agent = TestAgent(model=AsyncMock())
    config = TestConfig()

    with patch.object(agent, "load_prompt", return_value="template prompt") as mock_load:
        prompt = agent.get_prompt(config, "generate.j2", topic="test")
        assert prompt == "template prompt"
        mock_load.assert_called_once_with("generate.j2", topic="test")
```

```bash
cd server && .venv/bin/python -m pytest tests/test_agent_prompt_override.py -v
```

- [ ] **Step 2: Add `get_prompt()` method to BaseAgent**

Modify `server/src/agents/base.py` — add method after `validate_outputs`:

```python
    def get_prompt(self, config: BaseModel, template_name: str, **kwargs) -> str:
        """Get prompt — uses _prompt_override from config if present, otherwise loads Jinja2 template."""
        override = getattr(config, "_prompt_override", None)
        if override:
            return override
        return self.load_prompt(template_name, **kwargs)
```

- [ ] **Step 3: Update all 5 agents to use `get_prompt()`**

Modify `server/src/agents/topic_generator/agent.py` — replace `self.load_prompt(...)` call:

```python
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: TopicGenConfig = config
        brief = UserBrief.model_validate(inputs["user_brief"])

        prompt = self.get_prompt(
            config,
            "generate.j2",
            topic=brief.topic,
            keywords=brief.keywords,
            style=cfg.style or brief.style,
            platform_hints=brief.platform_hints,
            count=cfg.count,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            json_str = extract_json(response)
            raw_topics = json.loads(json_str)
            if not isinstance(raw_topics, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(
                f"Failed to parse topic generation response: {e}\nRaw response: {response[:500]}"
            ) from e

        topics = [Topic.model_validate(t).model_dump() for t in raw_topics]
        selected = max(topics, key=lambda t: t.get("score", 0)) if topics else None

        return {"topics": topics, "selected_topic": selected}
```

Modify `server/src/agents/material_collector/agent.py` — replace `self.load_prompt(...)`:

```python
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: MaterialCollectConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])

        prompt = self.get_prompt(
            config,
            "collect.j2",
            title=topic.title,
            angle=topic.angle,
            max_items=cfg.max_items,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_materials = json.loads(extract_json(response))
            if not isinstance(raw_materials, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse materials response: {e}\nRaw: {response[:500]}") from e

        materials = [Material.model_validate(m).model_dump() for m in raw_materials]
        return {"materials": materials}
```

Modify `server/src/agents/content_generator/agent.py` — replace `self.load_prompt(...)`:

```python
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ContentGenConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])
        materials = [Material.model_validate(m) for m in inputs.get("materials", [])]

        try:
            platform = get_platform(cfg.platform)
            platform_rules = platform.get_rules_prompt()
        except ValueError:
            platform_rules = f"Platform: {cfg.platform}"

        prompt = self.get_prompt(
            config,
            "generate.j2",
            platform=cfg.platform,
            format=cfg.format,
            topic_title=topic.title,
            topic_angle=topic.angle,
            materials=[m.model_dump() for m in materials],
            platform_rules=platform_rules,
            style=cfg.style,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_content = json.loads(extract_json(response))
            if not isinstance(raw_content, dict):
                raise ValueError("Expected a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse content generation response: {e}\nRaw: {response[:500]}") from e

        content = PlatformContent(
            platform=cfg.platform,
            title=raw_content.get("title", ""),
            body=raw_content.get("body", ""),
            tags=raw_content.get("tags", []),
            image_paths=[],
            image_prompts=raw_content.get("image_prompts", []),
        )

        return {"contents": {cfg.platform: content.model_dump()}}
```

Modify `server/src/agents/reviewer/agent.py` — replace `self.load_prompt(...)`:

```python
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ReviewerConfig = config
        contents: dict[str, dict] = inputs.get("contents", {})
        reviews: dict[str, dict] = {}

        for platform_name, content_data in contents.items():
            content = PlatformContent.model_validate(content_data)

            try:
                platform = get_platform(platform_name)
                platform_issues = platform.validate(content_data)
                platform_rules = platform.get_rules_prompt()
            except ValueError:
                platform_issues = []
                platform_rules = ""

            prompt = self.get_prompt(
                config,
                "review.j2",
                platform=platform_name,
                title=content.title,
                body=content.body,
                tags=content.tags,
                platform_rules=platform_rules,
                rules=cfg.rules,
            )

            response = await self.model.generate(prompt, temperature=cfg.temperature)

            try:
                raw_review = json.loads(extract_json(response))
            except (json.JSONDecodeError, ValueError):
                raw_review = {"score": 0.0, "issues": ["Failed to parse review"], "suggestions": []}

            score = raw_review.get("score", 0.0)
            all_issues = platform_issues + raw_review.get("issues", [])
            passed = score >= cfg.min_score and len(platform_issues) == 0

            review = ReviewResult(
                platform=platform_name,
                passed=passed,
                score=score,
                issues=all_issues,
                suggestions=raw_review.get("suggestions", []),
            )
            reviews[platform_name] = review.model_dump()

        return {"reviews": reviews}
```

Modify `server/src/agents/analyst/agent.py` — replace `self.load_prompt(...)`:

```python
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: AnalystConfig = config

        prompt = self.get_prompt(
            config,
            "analyze.j2",
            contents=inputs.get("contents", {}),
            reviews=inputs.get("reviews", {}),
            metrics=cfg.metrics,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_analysis = json.loads(extract_json(response))
        except (json.JSONDecodeError, ValueError):
            raw_analysis = {
                "summary": "Analysis failed to parse",
                "insights": [],
                "improvement_suggestions": [],
            }

        analysis = Analysis.model_validate(raw_analysis)
        return {"analysis": analysis.model_dump()}
```

- [ ] **Step 4: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_agent_prompt_override.py -v
```

- [ ] **Step 5: Commit**

```
feat(agents): 所有 Agent 支持 prompt_override

BaseAgent 新增 get_prompt() 方法，5 个 Agent 统一使用，支持运行时覆盖提示词。
```

---

## Task 5: Engine rerun_from_stage() method

**Files:**
- Modify: `server/src/core/engine.py`
- Create: `server/tests/test_engine_rerun.py`

**Depends on:** Task 1, Task 2, Task 3, Task 4

- [ ] **Step 1: Write tests for rerun_from_stage**

Create `server/tests/test_engine_rerun.py`:

```python
"""Tests for Engine.rerun_from_stage()."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from src.core.engine import Engine
from src.core.config import AppConfig, ModelsConfig, ModelConfig, StorageConfig, ServerConfig
from src.storage.state_store import StateStore


def _make_config(tmp_path) -> AppConfig:
    return AppConfig(
        models=ModelsConfig(
            text=ModelConfig(provider="minimax", api_key="fake", base_url="http://fake", model="test"),
            image=ModelConfig(provider="minimax", api_key="fake", base_url="http://fake", model="test"),
        ),
        storage=StorageConfig(
            db_path=str(tmp_path / "test.db"),
            assets_dir=str(tmp_path / "assets"),
            outputs_dir=str(tmp_path / "outputs"),
        ),
        server=ServerConfig(),
    )


@pytest.fixture
async def engine_with_run(tmp_path):
    """Create an engine with a completed run that has snapshots."""
    config = _make_config(tmp_path)
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()

    # Create a simple 2-stage pipeline YAML
    (pipelines_dir / "test.yaml").write_text("""
name: test_pipeline
description: test
platforms: [test_platform]
stages:
  - agent: topic_generator
    config:
      style: ""
      count: 3
  - agent: content_generator
    config:
      platform: test_platform
      format: image_text
""")

    engine = Engine(config, pipelines_dir)
    await engine.state_store.initialize()

    # Seed a completed run
    run_id = "testrun123"
    state = {
        "run_id": run_id,
        "pipeline_name": "test_pipeline",
        "user_brief": {"topic": "AI", "keywords": [], "platform_hints": [], "style": "", "extra": {}},
        "topics": [{"title": "AI trends", "angle": "2026", "score": 8.0, "reasoning": "hot"}],
        "selected_topic": {"title": "AI trends", "angle": "2026", "score": 8.0, "reasoning": "hot"},
        "materials": [],
        "contents": {"test_platform": {"platform": "test_platform", "title": "Old Title", "body": "Old body", "tags": [], "image_paths": [], "image_prompts": []}},
        "reviews": {},
        "analysis": {},
        "stage": "completed",
        "errors": [],
        "metadata": {"pipeline_file": "test"},
    }
    await engine.state_store.save_run(run_id, "test_pipeline", "completed", state)

    # Save snapshots for both stages
    await engine.state_store.save_snapshot(
        run_id=run_id, agent="topic_generator", version=1, status="completed",
        config={"params": {"count": 3}},
        inputs={"user_brief": state["user_brief"]},
        outputs={"topics": state["topics"], "selected_topic": state["selected_topic"]},
        error=None, duration_ms=1000,
    )
    await engine.state_store.save_snapshot(
        run_id=run_id, agent="content_generator", version=1, status="completed",
        config={"params": {"platform": "test_platform"}},
        inputs={"selected_topic": state["selected_topic"], "materials": []},
        outputs={"contents": state["contents"]},
        error=None, duration_ms=2000,
    )

    yield engine, run_id, state
    await engine.state_store.close()


@pytest.mark.asyncio
async def test_rerun_from_stage_not_found(engine_with_run):
    """rerun_from_stage raises error for nonexistent run."""
    engine, _, _ = engine_with_run
    with pytest.raises(ValueError, match="not found"):
        await engine.rerun_from_stage("nonexistent", "topic_generator")


@pytest.mark.asyncio
async def test_rerun_from_stage_agent_not_found(engine_with_run):
    """rerun_from_stage raises error for nonexistent agent snapshot."""
    engine, run_id, _ = engine_with_run
    with pytest.raises(ValueError, match="No snapshot found"):
        await engine.rerun_from_stage(run_id, "nonexistent_agent")
```

```bash
cd server && .venv/bin/python -m pytest tests/test_engine_rerun.py -v
```

- [ ] **Step 2: Implement rerun_from_stage in Engine**

Modify `server/src/core/engine.py` — add the method and update `run_pipeline` to pass `state_store`:

```python
"""High-level engine facade — wires together all components."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.core.config import AppConfig, ModelConfig
from src.core.models import create_model_adapter, ModelAdapter
from src.core.orchestrator import Orchestrator
from src.core.pipeline_loader import load_pipeline
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, StageConfig, UserBrief
from src.storage.state_store import StateStore
from src.storage.asset_store import AssetStore


class Engine:
    def __init__(self, config: AppConfig, pipelines_dir: Path) -> None:
        self.config = config
        self.pipelines_dir = pipelines_dir
        self.text_model: ModelAdapter = create_model_adapter(config.models.text)
        self.registry = AgentRegistry()
        self.orchestrator = Orchestrator(self.registry)
        self.state_store = StateStore(config.storage.db_path)
        self.asset_store = AssetStore(config.storage.assets_dir, config.storage.outputs_dir)

    async def initialize(self) -> None:
        await self.state_store.initialize()
        self._register_agents()

    def _register_agents(self) -> None:
        from src.agents.topic_generator import TopicGeneratorAgent
        from src.agents.material_collector import MaterialCollectorAgent
        from src.agents.content_generator import ContentGeneratorAgent
        from src.agents.reviewer import ReviewerAgent
        from src.agents.analyst import AnalystAgent

        for agent_cls in [TopicGeneratorAgent, MaterialCollectorAgent, ContentGeneratorAgent, ReviewerAgent, AnalystAgent]:
            self.registry.register(agent_cls, model=self.text_model)

    def load_pipeline(self, name: str) -> PipelineConfig:
        yaml_file = self.pipelines_dir / f"{name}.yaml"
        return load_pipeline(yaml_file)

    async def run_pipeline(self, pipeline_name: str, brief: UserBrief) -> dict:
        pipeline_config = self.load_pipeline(pipeline_name)
        run_id = uuid.uuid4().hex[:12]
        await self.state_store.save_run(run_id, pipeline_name, "running", {})

        try:
            result = await self.orchestrator.run(
                pipeline_config, brief, run_id=run_id,
                state_store=self.state_store,
            )

            for platform, content_data in result.get("contents", {}).items():
                content_id = f"{run_id}-{platform}"
                review = result.get("reviews", {}).get(platform, {})
                status = "approved" if review.get("passed", False) else "pending_review"
                await self.state_store.save_content(
                    content_id=content_id, run_id=run_id, platform=platform,
                    title=content_data.get("title", ""), body=content_data.get("body", ""),
                    status=status, tags=content_data.get("tags", []),
                    image_paths=content_data.get("image_paths", []),
                )

            await self.state_store.update_run(run_id, status=result.get("stage", "completed"), state=result)
            return {"run_id": run_id, "status": result.get("stage", "completed"), **result}

        except Exception as e:
            await self.state_store.update_run(run_id, status="failed", state={"error": str(e)})
            return {"run_id": run_id, "status": "failed", "error": str(e)}

    async def rerun_from_stage(
        self,
        run_id: str,
        from_agent: str,
        config_overrides: dict | None = None,
        model_override: str | None = None,
        prompt_override: str | None = None,
        only: bool = False,
    ) -> dict:
        """Rerun pipeline from a specific stage, optionally cascading to all downstream stages.

        Args:
            run_id: The run to rerun from.
            from_agent: The agent name to start rerun from.
            config_overrides: Config params to merge for the target agent.
            model_override: Override model name for the target agent.
            prompt_override: Override prompt for the target agent.
            only: If True, only rerun this one stage (no cascade).

        Returns:
            Updated run state dict.
        """
        # 1. Load the run
        run = await self.state_store.get_run(run_id)
        if run is None:
            raise ValueError(f"Run '{run_id}' not found")

        # 2. Get the snapshot for from_agent to read its inputs
        snapshot = await self.state_store.get_snapshot(run_id, from_agent)
        if snapshot is None:
            raise ValueError(f"No snapshot found for agent '{from_agent}' in run '{run_id}'")

        # 3. Load pipeline config to get stage order
        run_state = run["state"]
        pipeline_name = run.get("pipeline_name", "")

        # Try to find the pipeline file — check metadata first, then search
        pipeline_config = None
        metadata_file = run_state.get("metadata", {}).get("pipeline_file")
        if metadata_file:
            try:
                pipeline_config = self.load_pipeline(metadata_file)
            except Exception:
                pass

        if pipeline_config is None:
            # Try loading by pipeline_name (search pipelines_dir for matching name)
            for yaml_file in self.pipelines_dir.glob("*.yaml"):
                try:
                    pc = load_pipeline(yaml_file)
                    if pc.name == pipeline_name:
                        pipeline_config = pc
                        break
                except Exception:
                    continue

        if pipeline_config is None:
            raise ValueError(f"Cannot find pipeline config for '{pipeline_name}'")

        stage_agents = [s.agent for s in pipeline_config.stages]
        if from_agent not in stage_agents:
            raise ValueError(f"Agent '{from_agent}' not found in pipeline stages: {stage_agents}")

        from_idx = stage_agents.index(from_agent)

        # 4. Determine which stages to rerun
        if only:
            stages_to_rerun = [pipeline_config.stages[from_idx]]
        else:
            stages_to_rerun = pipeline_config.stages[from_idx:]

        # 5. Build current state from run's saved state
        current_state = dict(run_state)

        # 6. Rerun each stage sequentially
        await self.state_store.update_run(run_id, status="running")

        for i, stage in enumerate(stages_to_rerun):
            agent = self.registry.get(stage.agent)

            # Build effective stage config
            effective_config = dict(stage.config)
            effective_model = stage.model_override
            effective_prompt = stage.prompt_override

            # Apply overrides only to the first (target) stage
            if i == 0:
                if config_overrides:
                    effective_config.update(config_overrides)
                if model_override:
                    effective_model = model_override
                if prompt_override:
                    effective_prompt = prompt_override

            effective_stage = stage.model_copy(update={
                "config": effective_config,
                "model_override": effective_model,
                "prompt_override": effective_prompt,
            })

            # For the first stage, use inputs from snapshot; for subsequent, build from current state
            if i == 0:
                inputs = snapshot["inputs"]
            else:
                inputs = {key: current_state[key] for key in agent.consumes if key in current_state}

            # Validate config and inject prompt override
            config = agent.config_schema.model_validate(effective_config)
            if effective_prompt:
                object.__setattr__(config, "_prompt_override", effective_prompt)

            # Get next version
            version = await self.state_store.get_next_version(run_id, stage.agent)

            # Build config dict for snapshot
            snapshot_config = {
                "model": effective_model or "default",
                "model_provider": effective_stage.model_provider,
                "prompt_override": effective_prompt,
                "params": effective_config,
            }

            # Save running snapshot
            await self.state_store.save_snapshot(
                run_id=run_id, agent=stage.agent, version=version,
                status="running", config=snapshot_config,
                inputs=inputs, outputs=None, error=None, duration_ms=None,
            )

            import time
            start = time.monotonic()
            try:
                outputs = await agent.run(inputs, config)
                duration_ms = int((time.monotonic() - start) * 1000)

                # Update snapshot to completed
                await self.state_store._db.execute(
                    """UPDATE stage_snapshots
                       SET status = ?, outputs_json = ?, duration_ms = ?
                       WHERE run_id = ? AND agent = ? AND version = ?""",
                    ("completed", json.dumps(outputs, ensure_ascii=False), duration_ms, run_id, stage.agent, version),
                )
                await self.state_store._db.commit()

                # Merge outputs into current state
                for key, value in outputs.items():
                    if isinstance(value, dict) and isinstance(current_state.get(key), dict):
                        merged = dict(current_state[key])
                        merged.update(value)
                        current_state[key] = merged
                    else:
                        current_state[key] = value

            except Exception as e:
                duration_ms = int((time.monotonic() - start) * 1000)
                await self.state_store._db.execute(
                    """UPDATE stage_snapshots
                       SET status = ?, error = ?, duration_ms = ?
                       WHERE run_id = ? AND agent = ? AND version = ?""",
                    ("failed", str(e), duration_ms, run_id, stage.agent, version),
                )
                await self.state_store._db.commit()

                current_state["stage"] = "failed"
                errors = list(current_state.get("errors", []))
                errors.append({
                    "agent": stage.agent,
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "recoverable": False,
                })
                current_state["errors"] = errors
                await self.state_store.update_run(run_id, status="failed", state=current_state)
                return {"run_id": run_id, "status": "failed", **current_state}

        # 7. Update run state
        current_state["stage"] = "completed"
        await self.state_store.update_run(run_id, status="completed", state=current_state)
        return {"run_id": run_id, "status": "completed", **current_state}

    async def close(self) -> None:
        await self.state_store.close()
        await self.text_model.close()
```

- [ ] **Step 3: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_engine_rerun.py -v
```

- [ ] **Step 4: Commit**

```
feat(engine): 新增 rerun_from_stage 级联重跑方法

支持从指定节点开始重跑（可选仅重跑单节点），自动保存新版本快照并更新 run 状态。
```

---

## Task 6: API endpoints (stages router)

**Files:**
- Create: `server/src/api/routes/stages.py`
- Modify: `server/src/api/schemas.py`
- Modify: `server/src/api/app.py`
- Create: `server/tests/test_api_stages.py`

**Depends on:** Task 1, Task 5

- [ ] **Step 1: Write tests for stages API**

Create `server/tests/test_api_stages.py`:

```python
"""Tests for stages API routes."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from src.api.app import create_app
from src.storage.state_store import StateStore


@pytest.fixture
async def seeded_store(tmp_path):
    """A StateStore with pre-seeded snapshot data."""
    store = StateStore(str(tmp_path / "test.db"))
    await store.initialize()

    # Save a run
    await store.save_run("run1", "test_pipeline", "completed", {"stage": "completed"})

    # Save snapshots
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={"model": "test", "params": {"count": 5}},
        inputs={"user_brief": {"topic": "AI"}},
        outputs={"topics": [{"title": "AI trends"}]},
        error=None, duration_ms=1200,
    )
    await store.save_snapshot(
        run_id="run1", agent="content_generator", version=1, status="completed",
        config={"model": "test", "params": {"platform": "xiaohongshu"}},
        inputs={"selected_topic": {"title": "AI trends"}},
        outputs={"contents": {"xiaohongshu": {"title": "Test"}}},
        error=None, duration_ms=2500,
    )
    yield store
    await store.close()


@pytest.fixture
def client(seeded_store):
    """Test client with mocked store."""
    app = create_app()

    # Patch _get_store to return our seeded store
    with patch("src.api.routes.stages._get_store", return_value=seeded_store):
        with patch("src.api.routes.stages._store_initialized", return_value=seeded_store):
            client = TestClient(app)
            yield client


@pytest.mark.asyncio
async def test_list_stages(seeded_store):
    """GET /api/runs/{run_id}/stages returns latest snapshots."""
    snapshots = await seeded_store.list_snapshots("run1")
    assert len(snapshots) == 2
    agents = {s["agent"] for s in snapshots}
    assert agents == {"topic_generator", "content_generator"}


@pytest.mark.asyncio
async def test_get_stage(seeded_store):
    """GET /api/runs/{run_id}/stages/{agent} returns snapshot."""
    snap = await seeded_store.get_snapshot("run1", "topic_generator")
    assert snap is not None
    assert snap["agent"] == "topic_generator"
    assert snap["status"] == "completed"


@pytest.mark.asyncio
async def test_get_stage_history(seeded_store):
    """GET /api/runs/{run_id}/stages/{agent}/history returns all versions."""
    # Add a v2 snapshot
    await seeded_store.save_snapshot(
        run_id="run1", agent="topic_generator", version=2, status="completed",
        config={}, inputs={}, outputs={"v": 2}, error=None, duration_ms=800,
    )
    history = await seeded_store.list_snapshot_history("run1", "topic_generator")
    assert len(history) == 2
    assert history[0]["version"] == 1
    assert history[1]["version"] == 2


@pytest.mark.asyncio
async def test_edit_stage_outputs(seeded_store):
    """PUT /api/runs/{run_id}/stages/{agent} creates updated snapshot."""
    await seeded_store.update_snapshot_outputs(
        "run1", "topic_generator", 1,
        outputs={"topics": [{"title": "Edited AI trends"}]},
    )
    snap = await seeded_store.get_snapshot("run1", "topic_generator", version=1)
    assert snap["outputs"]["topics"][0]["title"] == "Edited AI trends"
```

```bash
cd server && .venv/bin/python -m pytest tests/test_api_stages.py -v
```

- [ ] **Step 2: Add API schemas for stages**

Modify `server/src/api/schemas.py`:

```python
"""API request/response schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    pipeline: str
    brief: str
    keywords: list[str] = Field(default_factory=list)
    platform_hints: list[str] = Field(default_factory=list)
    stage_overrides: dict[str, dict] = Field(default_factory=dict)


class RunPipelineResponse(BaseModel):
    run_id: str
    status: str


class ApproveRequest(BaseModel):
    publish_url: str = ""


# ── Stage Supervision Schemas ─────────────────────────────────────


class EditStageRequest(BaseModel):
    """Edit a stage's outputs."""
    outputs: dict


class RerunStageRequest(BaseModel):
    """Rerun from a stage with optional overrides."""
    config: dict = Field(default_factory=dict)
    model: str | None = None
    prompt: str | None = None
    only: bool = False
```

- [ ] **Step 3: Create stages router**

Create `server/src/api/routes/stages.py`:

```python
"""API routes for stage snapshot operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas import EditStageRequest, RerunStageRequest
from src.core.config import load_config
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/runs", tags=["stages"])

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", _PROJECT_ROOT / "config.yaml"))


def _get_store() -> StateStore:
    config = load_config(_get_config_path())
    return StateStore(config.storage.db_path)


async def _store_initialized() -> StateStore:
    store = _get_store()
    await store.initialize()
    return store


@router.get("/{run_id}/stages")
async def list_stages(run_id: str):
    """List all stage snapshots (latest version per agent) for a run."""
    store = await _store_initialized()
    try:
        snapshots = await store.list_snapshots(run_id)
        return snapshots
    finally:
        await store.close()


@router.get("/{run_id}/stages/{agent}")
async def get_stage(run_id: str, agent: str, version: Optional[int] = None):
    """Get a stage snapshot. Returns latest version by default."""
    store = await _store_initialized()
    try:
        snap = await store.get_snapshot(run_id, agent, version=version)
        if snap is None:
            raise HTTPException(status_code=404, detail=f"Snapshot not found: {agent} in run {run_id}")
        return snap
    finally:
        await store.close()


@router.get("/{run_id}/stages/{agent}/history")
async def get_stage_history(run_id: str, agent: str):
    """Get all versions of a stage snapshot."""
    store = await _store_initialized()
    try:
        history = await store.list_snapshot_history(run_id, agent)
        return history
    finally:
        await store.close()


@router.put("/{run_id}/stages/{agent}")
async def edit_stage(run_id: str, agent: str, body: EditStageRequest):
    """Edit a stage's outputs — saves as new version."""
    store = await _store_initialized()
    try:
        # Get current latest snapshot
        snap = await store.get_snapshot(run_id, agent)
        if snap is None:
            raise HTTPException(status_code=404, detail=f"Snapshot not found: {agent} in run {run_id}")

        # Save new version with edited outputs
        new_version = await store.get_next_version(run_id, agent)
        await store.save_snapshot(
            run_id=run_id,
            agent=agent,
            version=new_version,
            status="edited",
            config=snap["config"],
            inputs=snap["inputs"],
            outputs=body.outputs,
            error=None,
            duration_ms=None,
        )

        return {"agent": agent, "version": new_version, "status": "edited"}
    finally:
        await store.close()


@router.post("/{run_id}/stages/{agent}/rerun")
async def rerun_stage(run_id: str, agent: str, body: RerunStageRequest):
    """Rerun from a stage with optional config/model/prompt overrides."""
    from src.core.engine import Engine

    config = load_config(_get_config_path())
    pipelines_dir = Path(os.environ.get("SP_PIPELINES_DIR", _PROJECT_ROOT / "pipelines"))
    engine = Engine(config, pipelines_dir)
    try:
        await engine.initialize()
        result = await engine.rerun_from_stage(
            run_id=run_id,
            from_agent=agent,
            config_overrides=body.config if body.config else None,
            model_override=body.model,
            prompt_override=body.prompt,
            only=body.only,
        )
        return {"run_id": run_id, "status": result.get("status", "completed")}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        await engine.close()
```

- [ ] **Step 4: Register stages router in app.py**

Modify `server/src/api/app.py`:

```python
"""FastAPI application factory."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import pipelines, contents, runs, stages
from src.api import sse

def create_app() -> FastAPI:
    app = FastAPI(
        title="SuperPipeline API",
        description="Multi-agent content production pipeline",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(pipelines.router)
    app.include_router(contents.router)
    app.include_router(runs.router)
    app.include_router(stages.router)
    app.include_router(sse.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 5: Update runs.py to pass state_store to orchestrator**

Modify `server/src/api/routes/runs.py` — update `_execute_pipeline_bg` to pass state_store:

Find this line in `_execute_pipeline_bg`:
```python
        result = await engine.orchestrator.run(pipeline_config, brief, run_id=run_id, stage_overrides=stage_overrides)
```

Replace with:
```python
        result = await engine.orchestrator.run(
            pipeline_config, brief, run_id=run_id,
            stage_overrides=stage_overrides,
            state_store=engine.state_store,
        )
```

- [ ] **Step 6: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_api_stages.py -v
```

- [ ] **Step 7: Commit**

```
feat(api): 新增 stages 路由，支持快照查询/编辑/重跑

5 个端点覆盖完整节点监督 API：list/get/edit/rerun/history。
```

---

## Task 7: CLI commands (sp stage)

**Files:**
- Create: `server/src/cli/commands/stage.py`
- Modify: `server/src/cli/app.py`
- Create: `server/tests/test_cli_stage.py`

**Depends on:** Task 1, Task 5

- [ ] **Step 1: Write tests for CLI stage commands**

Create `server/tests/test_cli_stage.py`:

```python
"""Tests for CLI stage commands."""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch, AsyncMock
from typer.testing import CliRunner

from src.cli.app import app
from src.storage.state_store import StateStore


runner = CliRunner()


@pytest.fixture
async def store(tmp_path):
    s = StateStore(str(tmp_path / "test.db"))
    await s.initialize()
    # Seed data
    await s.save_run("run1", "test_pipeline", "completed", {})
    await s.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={"model": "test", "params": {"count": 5}},
        inputs={"user_brief": {"topic": "AI"}},
        outputs={"topics": [{"title": "AI trends"}]},
        error=None, duration_ms=1200,
    )
    await s.save_snapshot(
        run_id="run1", agent="content_generator", version=1, status="completed",
        config={"model": "test", "params": {"platform": "xhs"}},
        inputs={"selected_topic": {"title": "AI trends"}},
        outputs={"contents": {"xhs": {"title": "Test"}}},
        error=None, duration_ms=2500,
    )
    yield s
    await s.close()


def test_stage_list(store):
    """sp stage list <run_id> shows stages."""
    with patch("src.cli.commands.stage._get_store", return_value=store):
        result = runner.invoke(app, ["stage", "list", "run1", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 2


def test_stage_show(store):
    """sp stage show <run_id> <agent> shows snapshot."""
    with patch("src.cli.commands.stage._get_store", return_value=store):
        result = runner.invoke(app, ["stage", "show", "run1", "topic_generator", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["agent"] == "topic_generator"
        assert data["status"] == "completed"


def test_stage_show_field(store):
    """sp stage show --field extracts a nested field."""
    with patch("src.cli.commands.stage._get_store", return_value=store):
        result = runner.invoke(app, [
            "stage", "show", "run1", "topic_generator",
            "--field", "outputs.topics",
            "--format", "json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert data[0]["title"] == "AI trends"


def test_stage_history(store):
    """sp stage history <run_id> <agent> shows versions."""
    with patch("src.cli.commands.stage._get_store", return_value=store):
        result = runner.invoke(app, ["stage", "history", "run1", "topic_generator", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["version"] == 1
```

```bash
cd server && .venv/bin/python -m pytest tests/test_cli_stage.py -v
```

- [ ] **Step 2: Create stage CLI commands**

Create `server/src/cli/commands/stage.py`:

```python
"""CLI command: sp stage list / show / edit / rerun / history."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer

from src.cli.formatters import output, console
from src.core.config import load_config
from src.storage.state_store import StateStore

app = typer.Typer(help="Inspect and manipulate stage snapshots")


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)


def _resolve_field(data: dict, field_path: str):
    """Resolve a dot-separated field path like 'outputs.topics'."""
    parts = field_path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


@app.command("list")
def stage_list(
    run_id: str = typer.Argument(help="Run ID"),
    fmt: str = typer.Option("table", "--format", help="Output format: table | json"),
) -> None:
    """List all stage snapshots (latest version) for a run."""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        snapshots = await store.list_snapshots(run_id)
        await store.close()
        return snapshots

    snapshots = asyncio.run(_fetch())
    if not snapshots:
        console.print(f"No snapshots found for run '{run_id}'")
        return

    if fmt == "json":
        output(snapshots, "json")
    else:
        # Build summary rows
        rows = []
        for s in snapshots:
            outputs = s.get("outputs") or {}
            preview = json.dumps(outputs, ensure_ascii=False)[:80] + "..." if outputs else "-"
            rows.append({
                "agent": s["agent"],
                "version": s["version"],
                "status": s["status"],
                "duration_ms": s.get("duration_ms", "-"),
                "output_preview": preview,
            })
        output(rows, "table", columns=["agent", "version", "status", "duration_ms", "output_preview"])


@app.command("show")
def stage_show(
    run_id: str = typer.Argument(help="Run ID"),
    agent: str = typer.Argument(help="Agent name"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Specific version (default: latest)"),
    field: Optional[str] = typer.Option(None, "--field", "-f", help="Extract a specific field (dot path)"),
    fmt: str = typer.Option("json", "--format", help="Output format"),
) -> None:
    """Show full snapshot for a stage."""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        snap = await store.get_snapshot(run_id, agent, version=version)
        await store.close()
        return snap

    snap = asyncio.run(_fetch())
    if snap is None:
        typer.echo(f"Snapshot not found: {agent} in run {run_id}", err=True)
        raise typer.Exit(code=4)

    if field:
        value = _resolve_field(snap, field)
        if value is None:
            typer.echo(f"Field '{field}' not found in snapshot", err=True)
            raise typer.Exit(code=4)
        output(value, fmt)
    else:
        output(snap, fmt)


@app.command("edit")
def stage_edit(
    run_id: str = typer.Argument(help="Run ID"),
    agent: str = typer.Argument(help="Agent name"),
    set_field: Optional[str] = typer.Option(None, "--set", help="Set a field: 'outputs.contents.xhs.title=New Title'"),
    file: Optional[Path] = typer.Option(None, "--file", help="Load full outputs from JSON file"),
    field: Optional[str] = typer.Option(None, "--field", help="Field path to edit"),
    value: Optional[str] = typer.Option(None, "--value", help="Value for --field"),
    fmt: str = typer.Option("json", "--format", help="Output format"),
) -> None:
    """Edit a stage's outputs. Saves as a new version."""
    store = _get_store()

    async def _do_edit():
        await store.initialize()
        snap = await store.get_snapshot(run_id, agent)
        if snap is None:
            typer.echo(f"Snapshot not found: {agent} in run {run_id}", err=True)
            await store.close()
            raise typer.Exit(code=4)

        current_outputs = snap.get("outputs") or {}

        if file:
            new_outputs = json.loads(file.read_text())
        elif set_field:
            # Parse "path.to.key=value"
            if "=" not in set_field:
                typer.echo("--set requires format: 'path.to.key=value'", err=True)
                await store.close()
                raise typer.Exit(code=1)
            path, val = set_field.split("=", 1)
            # Try to parse as JSON, fall back to string
            try:
                parsed_val = json.loads(val)
            except json.JSONDecodeError:
                parsed_val = val

            new_outputs = dict(current_outputs)
            parts = path.split(".")
            target = new_outputs
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = parsed_val
        elif field and value is not None:
            new_outputs = dict(current_outputs)
            parts = field.split(".")
            target = new_outputs
            for part in parts[:-1]:
                if part not in target or not isinstance(target[part], dict):
                    target[part] = {}
                target = target[part]
            try:
                parsed_val = json.loads(value)
            except json.JSONDecodeError:
                parsed_val = value
            target[parts[-1]] = parsed_val
        else:
            typer.echo("Must provide one of: --set, --file, or --field + --value", err=True)
            await store.close()
            raise typer.Exit(code=1)

        new_version = await store.get_next_version(run_id, agent)
        await store.save_snapshot(
            run_id=run_id, agent=agent, version=new_version,
            status="edited", config=snap["config"],
            inputs=snap["inputs"], outputs=new_outputs,
            error=None, duration_ms=None,
        )
        await store.close()
        return {"agent": agent, "version": new_version, "status": "edited"}

    result = asyncio.run(_do_edit())
    output(result, fmt)


@app.command("rerun")
def stage_rerun(
    run_id: str = typer.Argument(help="Run ID"),
    agent: str = typer.Argument(help="Agent name to rerun from"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="JSON config overrides"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model name"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Override prompt text"),
    prompt_file: Optional[Path] = typer.Option(None, "--prompt-file", help="Read prompt from file"),
    only: bool = typer.Option(False, "--only", help="Only rerun this stage (no cascade)"),
    fmt: str = typer.Option("json", "--format", help="Output format"),
) -> None:
    """Rerun from a stage. Cascades to all downstream stages by default."""
    from src.core.engine import Engine

    config_overrides = json.loads(config) if config else None
    effective_prompt = prompt
    if prompt_file and prompt_file.exists():
        effective_prompt = prompt_file.read_text()

    async def _do_rerun():
        from src.core.config import load_config as _load_config
        config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
        pipelines_dir = Path(os.environ.get("SP_PIPELINES_DIR", Path(__file__).parent.parent.parent.parent / "pipelines"))
        app_config = _load_config(config_path)

        engine = Engine(app_config, pipelines_dir)
        await engine.initialize()
        try:
            result = await engine.rerun_from_stage(
                run_id=run_id,
                from_agent=agent,
                config_overrides=config_overrides,
                model_override=model,
                prompt_override=effective_prompt,
                only=only,
            )
            return result
        finally:
            await engine.close()

    try:
        result = asyncio.run(_do_rerun())
        output({"run_id": run_id, "status": result.get("status", "unknown")}, fmt)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=4)


@app.command("history")
def stage_history(
    run_id: str = typer.Argument(help="Run ID"),
    agent: str = typer.Argument(help="Agent name"),
    fmt: str = typer.Option("table", "--format", help="Output format: table | json"),
) -> None:
    """Show version history for a stage."""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        history = await store.list_snapshot_history(run_id, agent)
        await store.close()
        return history

    history = asyncio.run(_fetch())
    if not history:
        console.print(f"No history for {agent} in run {run_id}")
        return

    if fmt == "json":
        output(history, "json")
    else:
        rows = []
        for h in history:
            rows.append({
                "version": h["version"],
                "status": h["status"],
                "duration_ms": h.get("duration_ms", "-"),
                "created_at": h.get("created_at", ""),
            })
        output(rows, "table", columns=["version", "status", "duration_ms", "created_at"])
```

- [ ] **Step 3: Register stage sub-command in CLI app**

Modify `server/src/cli/app.py`:

```python
"""SuperPipeline CLI — main entry point."""

from __future__ import annotations

import typer

from src.cli.commands import pipeline as pipeline_cmd
from src.cli.commands.run import run_command
from src.cli.commands.status import status_command
from src.cli.commands import content as content_cmd
from src.cli.commands import agent as agent_cmd
from src.cli.commands import stage as stage_cmd

app = typer.Typer(
    name="sp",
    help="SuperPipeline — Multi-agent content production pipeline",
    no_args_is_help=True,
)

app.add_typer(pipeline_cmd.app, name="pipeline")
app.command("run")(run_command)
app.command("status")(status_command)
app.add_typer(content_cmd.app, name="content")
app.add_typer(agent_cmd.app, name="agent")
app.add_typer(stage_cmd.app, name="stage")


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Verify tests pass**

```bash
cd server && .venv/bin/python -m pytest tests/test_cli_stage.py -v
```

- [ ] **Step 5: Commit**

```
feat(cli): 新增 sp stage 子命令（list/show/edit/rerun/history）

CLI 完整覆盖节点监督操作，所有命令支持 --format json。
```

---

## Task 8: Frontend StageDetail component

**Files:**
- Modify: `web/src/lib/types.ts`
- Modify: `web/src/lib/api-client.ts`
- Create: `web/src/components/runs/StageDetail.tsx`
- Modify: `web/src/app/runs/[runId]/page.tsx`

**Depends on:** Task 6

- [ ] **Step 1: Add StageSnapshot type**

Modify `web/src/lib/types.ts` — add after the existing `PipelineEvent` interface:

```typescript
export interface StageSnapshot {
  id: number;
  run_id: string;
  agent: string;
  version: number;
  status: "running" | "completed" | "failed" | "edited";
  config: Record<string, any>;
  inputs: Record<string, any>;
  outputs: Record<string, any> | null;
  error: string | null;
  duration_ms: number | null;
  created_at: string;
}
```

- [ ] **Step 2: Add stages API methods**

Modify `web/src/lib/api-client.ts` — add to the `api` object:

```typescript
  // Stage supervision
  listStages: (runId: string) =>
    fetchApi<StageSnapshot[]>(`/api/runs/${runId}/stages`),
  getStage: (runId: string, agent: string, version?: number) => {
    const qs = version ? `?version=${version}` : "";
    return fetchApi<StageSnapshot>(`/api/runs/${runId}/stages/${agent}${qs}`);
  },
  getStageHistory: (runId: string, agent: string) =>
    fetchApi<StageSnapshot[]>(`/api/runs/${runId}/stages/${agent}/history`),
  editStage: (runId: string, agent: string, outputs: Record<string, any>) =>
    fetchApi<{ agent: string; version: number; status: string }>(
      `/api/runs/${runId}/stages/${agent}`,
      { method: "PUT", body: JSON.stringify({ outputs }) },
    ),
  rerunStage: (
    runId: string,
    agent: string,
    options?: { config?: Record<string, any>; model?: string; prompt?: string; only?: boolean },
  ) =>
    fetchApi<{ run_id: string; status: string }>(
      `/api/runs/${runId}/stages/${agent}/rerun`,
      {
        method: "POST",
        body: JSON.stringify({
          config: options?.config || {},
          model: options?.model || null,
          prompt: options?.prompt || null,
          only: options?.only || false,
        }),
      },
    ),
```

Also add the import at the top:
```typescript
import type { Run, Content, Pipeline, PipelineDetail, StageSnapshot } from "./types";
```

- [ ] **Step 3: Create StageDetail component**

Create `web/src/components/runs/StageDetail.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api-client";
import type { StageSnapshot } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Clock,
  RefreshCw,
  Pencil,
  History,
  ChevronDown,
  ChevronUp,
  X,
} from "lucide-react";

interface StageDetailProps {
  runId: string;
  agent: string;
  onClose: () => void;
  onRerun?: () => void;
}

function statusColor(status: string) {
  switch (status) {
    case "completed":
      return "bg-emerald-50 text-emerald-700 border-emerald-200";
    case "failed":
      return "bg-red-50 text-red-700 border-red-200";
    case "running":
      return "bg-blue-50 text-blue-700 border-blue-200";
    case "edited":
      return "bg-amber-50 text-amber-700 border-amber-200";
    default:
      return "";
  }
}

export function StageDetail({ runId, agent, onClose, onRerun }: StageDetailProps) {
  const [snapshot, setSnapshot] = useState<StageSnapshot | null>(null);
  const [history, setHistory] = useState<StageSnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showHistory, setShowHistory] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getStage(runId, agent),
      api.getStageHistory(runId, agent),
    ])
      .then(([snap, hist]) => {
        setSnapshot(snap);
        setHistory(hist);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [runId, agent]);

  function handleVersionChange(version: string) {
    const v = parseInt(version, 10);
    api.getStage(runId, agent, v).then(setSnapshot).catch((e) => setError(e.message));
  }

  function startEdit() {
    setEditText(JSON.stringify(snapshot?.outputs ?? {}, null, 2));
    setEditing(true);
  }

  async function saveEdit() {
    try {
      const outputs = JSON.parse(editText);
      await api.editStage(runId, agent, outputs);
      // Reload
      const [snap, hist] = await Promise.all([
        api.getStage(runId, agent),
        api.getStageHistory(runId, agent),
      ]);
      setSnapshot(snap);
      setHistory(hist);
      setEditing(false);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleRerun() {
    setRerunning(true);
    try {
      await api.rerunStage(runId, agent, { only: false });
      onRerun?.();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRerunning(false);
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="py-4 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-20" />
        </CardContent>
      </Card>
    );
  }

  if (!snapshot) {
    return (
      <Card>
        <CardContent className="py-4">
          <p className="text-sm text-muted-foreground">
            {error || `No snapshot data for ${agent}`}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-l-4 border-l-blue-400">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm font-mono">{agent}</CardTitle>
            <Badge
              variant="outline"
              className={`text-[10px] ${statusColor(snapshot.status)}`}
            >
              {snapshot.status}
            </Badge>
            {snapshot.duration_ms != null && (
              <span className="text-[11px] text-muted-foreground flex items-center gap-0.5">
                <Clock className="h-3 w-3" />
                {snapshot.duration_ms}ms
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {history.length > 1 && (
              <Select
                value={String(snapshot.version)}
                onValueChange={handleVersionChange}
              >
                <SelectTrigger className="h-7 w-20 text-[11px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {history.map((h) => (
                    <SelectItem key={h.version} value={String(h.version)}>
                      v{h.version}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0"
              onClick={startEdit}
              title="Edit outputs"
            >
              <Pencil className="h-3 w-3" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0"
              onClick={handleRerun}
              disabled={rerunning}
              title="Rerun from here"
            >
              <RefreshCw className={`h-3 w-3 ${rerunning ? "animate-spin" : ""}`} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 w-7 p-0"
              onClick={onClose}
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {error && <p className="text-[12px] text-red-500">{error}</p>}

        {/* Config */}
        <div>
          <p className="text-[11px] font-medium text-muted-foreground mb-1">Config</p>
          <pre className="text-[11px] bg-muted/50 rounded p-2 overflow-x-auto max-h-24">
            {JSON.stringify(snapshot.config, null, 2)}
          </pre>
        </div>

        {/* Inputs summary */}
        <div>
          <p className="text-[11px] font-medium text-muted-foreground mb-1">
            Inputs ({Object.keys(snapshot.inputs).join(", ")})
          </p>
          <pre className="text-[11px] bg-muted/50 rounded p-2 overflow-x-auto max-h-32">
            {JSON.stringify(snapshot.inputs, null, 2)}
          </pre>
        </div>

        {/* Outputs */}
        <div>
          <p className="text-[11px] font-medium text-muted-foreground mb-1">Outputs</p>
          {editing ? (
            <div className="space-y-2">
              <textarea
                className="w-full h-48 text-[11px] font-mono bg-muted/50 rounded p-2 border"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
              />
              <div className="flex gap-2">
                <Button size="sm" className="h-7 text-[11px]" onClick={saveEdit}>
                  Save as new version
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[11px]"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <pre className="text-[11px] bg-muted/50 rounded p-2 overflow-x-auto max-h-48">
              {snapshot.outputs
                ? JSON.stringify(snapshot.outputs, null, 2)
                : snapshot.error
                  ? `Error: ${snapshot.error}`
                  : "null"}
            </pre>
          )}
        </div>

        {/* History toggle */}
        {history.length > 1 && (
          <button
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
            onClick={() => setShowHistory(!showHistory)}
          >
            <History className="h-3 w-3" />
            {history.length} versions
            {showHistory ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
        {showHistory && (
          <div className="space-y-1">
            {history.map((h) => (
              <div
                key={h.version}
                className="flex items-center gap-3 text-[11px] text-muted-foreground"
              >
                <span className="font-mono">v{h.version}</span>
                <Badge variant="outline" className={`text-[9px] ${statusColor(h.status)}`}>
                  {h.status}
                </Badge>
                <span>{h.duration_ms != null ? `${h.duration_ms}ms` : "-"}</span>
                <span>{new Date(h.created_at).toLocaleString("zh-CN")}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Integrate StageDetail into run detail page**

Modify `web/src/app/runs/[runId]/page.tsx` — add a clickable node mechanism. Add after the existing imports:

```typescript
import { StageDetail } from "@/components/runs/StageDetail";
```

Add state for selected stage inside the `RunDetail` component, after existing state:

```typescript
  const [selectedStage, setSelectedStage] = useState<string | null>(null);
```

Add after the `{/* Pipeline Progress */}` Card and before `{/* Errors */}`:

```tsx
      {/* Stage Detail Panel */}
      {selectedStage && (
        <StageDetail
          runId={runId}
          agent={selectedStage}
          onClose={() => setSelectedStage(null)}
          onRerun={() => {
            // Reload run data after rerun
            api.getRun(runId).then(setRun).catch(() => {});
            setSelectedStage(null);
          }}
        />
      )}
```

Modify the `PipelineProgress` card to make stages clickable. Replace:

```tsx
      <Card>
        <CardContent className="py-5 flex justify-center">
          <PipelineProgress stageStatuses={stageStatuses} />
        </CardContent>
      </Card>
```

With:

```tsx
      <Card>
        <CardContent className="py-5 flex justify-center">
          <PipelineProgress
            stageStatuses={stageStatuses}
            onStageClick={(agent) => setSelectedStage(selectedStage === agent ? null : agent)}
            selectedStage={selectedStage}
          />
        </CardContent>
      </Card>
```

- [ ] **Step 5: Update PipelineProgress to support clicking**

Modify `web/src/components/runs/PipelineProgress.tsx` to accept `onStageClick` and `selectedStage` props. Add to the component's props interface:

```typescript
interface PipelineProgressProps {
  stageStatuses: Record<string, "pending" | "running" | "completed" | "failed">;
  onStageClick?: (agent: string) => void;
  selectedStage?: string | null;
}
```

Make each stage node clickable — wrap each stage element with an `onClick` handler and add a selected indicator (ring). The exact implementation depends on the current PipelineProgress code, but the key change is:

- Each stage node gets `onClick={() => onStageClick?.(agent)}` and `cursor-pointer`
- Selected stage gets an extra `ring-2 ring-blue-400` class

- [ ] **Step 6: Build verification**

```bash
cd web && npm run build
```

- [ ] **Step 7: Commit**

```
feat(web): 节点详情面板，支持查看/编辑/重跑快照

点击管道节点展开 StageDetail 面板，显示配置/输入/输出/版本历史，支持编辑输出和重跑。
```

---

## Task 9: Integration test

**Files:**
- Create: `server/tests/test_node_supervision_integration.py`

**Depends on:** Task 1-7

- [ ] **Step 1: Write end-to-end integration test**

Create `server/tests/test_node_supervision_integration.py`:

```python
"""Integration test for node supervision: run → snapshots → edit → rerun → cascade."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, patch

from src.core.config import AppConfig, ModelsConfig, ModelConfig, StorageConfig, ServerConfig
from src.core.engine import Engine
from src.core.state import UserBrief
from src.storage.state_store import StateStore
from pathlib import Path


MOCK_TOPIC_RESPONSE = json.dumps([
    {"title": "AI Trends 2026", "angle": "practical impact", "score": 9.0, "reasoning": "trending"},
    {"title": "Backup Topic", "angle": "academic", "score": 6.0, "reasoning": "niche"},
])

MOCK_MATERIAL_RESPONSE = json.dumps([
    {"source": "https://example.com", "title": "AI Report", "snippet": "Key data...", "source_type": "web"},
])

MOCK_CONTENT_RESPONSE = json.dumps({
    "title": "AI Trends You Need to Know",
    "body": "Content body here...",
    "tags": ["AI", "trends"],
    "image_prompts": [],
})

MOCK_REVIEW_RESPONSE = json.dumps({
    "score": 8.5,
    "issues": [],
    "suggestions": ["Add more data"],
})

MOCK_ANALYSIS_RESPONSE = json.dumps({
    "summary": "Strong content with good engagement potential",
    "insights": ["AI topic trending"],
    "improvement_suggestions": ["Add visuals"],
})

MOCK_RESPONSES = [
    MOCK_TOPIC_RESPONSE,
    MOCK_MATERIAL_RESPONSE,
    MOCK_CONTENT_RESPONSE,
    MOCK_REVIEW_RESPONSE,
    MOCK_ANALYSIS_RESPONSE,
]

# For rerun (content_generator + reviewer + analyst)
MOCK_RERUN_CONTENT = json.dumps({
    "title": "NEW AI Trends Title",
    "body": "Rerun content body...",
    "tags": ["AI", "2026"],
    "image_prompts": [],
})

MOCK_RERUN_REVIEW = json.dumps({
    "score": 9.0,
    "issues": [],
    "suggestions": [],
})

MOCK_RERUN_ANALYSIS = json.dumps({
    "summary": "Improved content after rerun",
    "insights": ["Better engagement"],
    "improvement_suggestions": [],
})


def _make_config(tmp_path) -> AppConfig:
    return AppConfig(
        models=ModelsConfig(
            text=ModelConfig(provider="minimax", api_key="fake", base_url="http://fake", model="test"),
            image=ModelConfig(provider="minimax", api_key="fake", base_url="http://fake", model="test"),
        ),
        storage=StorageConfig(
            db_path=str(tmp_path / "test.db"),
            assets_dir=str(tmp_path / "assets"),
            outputs_dir=str(tmp_path / "outputs"),
        ),
    )


@pytest.fixture
def pipeline_dir(tmp_path):
    d = tmp_path / "pipelines"
    d.mkdir()
    (d / "test.yaml").write_text("""
name: test_pipeline
description: Integration test pipeline
platforms:
  - xiaohongshu
stages:
  - agent: topic_generator
    config:
      style: ""
      count: 2
      temperature: 0.5
  - agent: material_collector
    config:
      max_items: 3
      temperature: 0.3
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
      temperature: 0.7
  - agent: reviewer
    config:
      min_score: 7.0
      temperature: 0.3
  - agent: analyst
    config:
      temperature: 0.5
""")
    return d


@pytest.mark.asyncio
async def test_full_pipeline_creates_snapshots(tmp_path, pipeline_dir):
    """Run pipeline → verify snapshots for all 5 stages."""
    config = _make_config(tmp_path)
    engine = Engine(config, pipeline_dir)

    response_idx = {"i": 0}

    async def mock_generate(prompt, **kwargs):
        idx = response_idx["i"]
        response_idx["i"] += 1
        return MOCK_RESPONSES[idx]

    with patch("src.core.models.MiniMaxAdapter.generate", side_effect=mock_generate):
        with patch("src.core.models.MiniMaxAdapter.__init__", return_value=None):
            engine.text_model = AsyncMock()
            engine.text_model.generate = mock_generate
            engine.text_model.close = AsyncMock()
            await engine.state_store.initialize()
            engine._register_agents()

            # Patch model on all registered agents
            for agent in engine.registry._agents.values():
                agent.model = engine.text_model

            brief = UserBrief(topic="AI trends", keywords=["artificial intelligence"])
            result = await engine.run_pipeline("test", brief)

    assert result["status"] == "completed"
    run_id = result["run_id"]

    # Verify snapshots exist for all stages
    snapshots = await engine.state_store.list_snapshots(run_id)
    assert len(snapshots) == 5

    agent_names = [s["agent"] for s in snapshots]
    assert "topic_generator" in agent_names
    assert "material_collector" in agent_names
    assert "content_generator" in agent_names
    assert "reviewer" in agent_names
    assert "analyst" in agent_names

    # All should be completed
    for s in snapshots:
        assert s["status"] == "completed", f"{s['agent']} status is {s['status']}"
        assert s["version"] == 1
        assert s["duration_ms"] is not None
        assert s["duration_ms"] >= 0

    # Verify topic_generator snapshot has correct data
    tg = await engine.state_store.get_snapshot(run_id, "topic_generator")
    assert len(tg["outputs"]["topics"]) == 2
    assert tg["inputs"]["user_brief"]["topic"] == "AI trends"

    await engine.state_store.close()


@pytest.mark.asyncio
async def test_edit_then_rerun_cascade(tmp_path, pipeline_dir):
    """Edit content_generator output → rerun from reviewer → verify cascade."""
    config = _make_config(tmp_path)
    engine = Engine(config, pipeline_dir)

    response_idx = {"i": 0}
    all_responses = MOCK_RESPONSES + [MOCK_RERUN_REVIEW, MOCK_RERUN_ANALYSIS]

    async def mock_generate(prompt, **kwargs):
        idx = response_idx["i"]
        response_idx["i"] += 1
        return all_responses[idx]

    engine.text_model = AsyncMock()
    engine.text_model.generate = mock_generate
    engine.text_model.close = AsyncMock()
    await engine.state_store.initialize()
    engine._register_agents()

    for agent in engine.registry._agents.values():
        agent.model = engine.text_model

    # Step 1: Run full pipeline
    brief = UserBrief(topic="AI trends", keywords=[])
    result = await engine.run_pipeline("test", brief)
    run_id = result["run_id"]
    assert result["status"] == "completed"

    # Step 2: Edit content_generator outputs
    cg_snap = await engine.state_store.get_snapshot(run_id, "content_generator")
    edited_outputs = dict(cg_snap["outputs"])
    edited_outputs["contents"]["xiaohongshu"]["title"] = "EDITED TITLE"
    new_version = await engine.state_store.get_next_version(run_id, "content_generator")
    await engine.state_store.save_snapshot(
        run_id=run_id, agent="content_generator", version=new_version,
        status="edited", config=cg_snap["config"],
        inputs=cg_snap["inputs"], outputs=edited_outputs,
        error=None, duration_ms=None,
    )

    # Verify edit
    cg_latest = await engine.state_store.get_snapshot(run_id, "content_generator")
    assert cg_latest["version"] == 2
    assert cg_latest["outputs"]["contents"]["xiaohongshu"]["title"] == "EDITED TITLE"

    # Step 3: Rerun from reviewer (cascade to analyst)
    # Update the run state to include edited contents
    run = await engine.state_store.get_run(run_id)
    state = run["state"]
    state["contents"] = edited_outputs["contents"]
    state["metadata"]["pipeline_file"] = "test"
    await engine.state_store.update_run(run_id, state=state)

    rerun_result = await engine.rerun_from_stage(run_id, "reviewer")
    assert rerun_result["status"] == "completed"

    # Verify new versions for reviewer and analyst
    reviewer_snap = await engine.state_store.get_snapshot(run_id, "reviewer")
    assert reviewer_snap["version"] == 2

    analyst_snap = await engine.state_store.get_snapshot(run_id, "analyst")
    assert analyst_snap["version"] == 2

    # Content generator should still be at version 2 (edited, not rerun)
    cg_final = await engine.state_store.get_snapshot(run_id, "content_generator")
    assert cg_final["version"] == 2

    # Version history
    reviewer_history = await engine.state_store.list_snapshot_history(run_id, "reviewer")
    assert len(reviewer_history) == 2

    await engine.state_store.close()
```

```bash
cd server && .venv/bin/python -m pytest tests/test_node_supervision_integration.py -v
```

- [ ] **Step 2: Fix any issues discovered during integration testing**

If tests fail, fix the underlying code and re-run.

- [ ] **Step 3: Commit**

```
test: 节点监督端到端集成测试

覆盖完整流程：运行管道→验证快照→编辑输出→级联重跑→验证版本递增。
```

---

## Task 10: All tests pass + final commit

**Depends on:** Task 1-9

- [ ] **Step 1: Run all tests**

```bash
cd server && .venv/bin/python -m pytest tests/ -v --tb=short
```

- [ ] **Step 2: Run web build**

```bash
cd web && npm run build
```

- [ ] **Step 3: Fix any remaining issues**

Address any test failures or build errors.

- [ ] **Step 4: Final commit**

```
chore: 节点监督功能全部实现，所有测试通过

包含：stage_snapshots 存储、orchestrator 快照集成、prompt_override、
级联重跑、API 端点、CLI 命令、前端节点详情面板、集成测试。
```

---

## File Change Summary

### New files (7)
- `server/tests/test_state_store_snapshots.py` — snapshot CRUD 测试
- `server/tests/test_state_models.py` — StageConfig 扩展测试
- `server/tests/test_orchestrator_snapshots.py` — orchestrator 快照测试
- `server/tests/test_agent_prompt_override.py` — prompt_override 测试
- `server/tests/test_engine_rerun.py` — rerun_from_stage 测试
- `server/tests/test_api_stages.py` — stages API 测试
- `server/tests/test_cli_stage.py` — CLI stage 命令测试
- `server/tests/test_node_supervision_integration.py` — 端到端集成测试
- `server/src/api/routes/stages.py` — stages API 路由
- `server/src/cli/commands/stage.py` — CLI stage 子命令
- `web/src/components/runs/StageDetail.tsx` — 节点详情组件

### Modified files (11)
- `server/src/storage/state_store.py` — stage_snapshots 表 + CRUD
- `server/src/core/state.py` — StageConfig 新增 3 个字段
- `server/src/core/orchestrator.py` — _wrap_agent 快照 + prompt_override
- `server/src/agents/base.py` — get_prompt() 方法
- `server/src/agents/topic_generator/agent.py` — 使用 get_prompt()
- `server/src/agents/material_collector/agent.py` — 使用 get_prompt()
- `server/src/agents/content_generator/agent.py` — 使用 get_prompt()
- `server/src/agents/reviewer/agent.py` — 使用 get_prompt()
- `server/src/agents/analyst/agent.py` — 使用 get_prompt()
- `server/src/core/engine.py` — rerun_from_stage() + state_store 传递
- `server/src/api/schemas.py` — EditStageRequest + RerunStageRequest
- `server/src/api/app.py` — 注册 stages router
- `server/src/api/routes/runs.py` — 传递 state_store
- `server/src/cli/app.py` — 注册 stage 子命令
- `web/src/lib/types.ts` — StageSnapshot 类型
- `web/src/lib/api-client.ts` — stages API 方法
- `web/src/app/runs/[runId]/page.tsx` — 集成 StageDetail
