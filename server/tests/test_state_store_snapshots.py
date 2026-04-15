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
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={"model": "MiniMax-M2.5", "params": {"count": 5}},
        inputs={"user_brief": {"topic": "AI"}},
        outputs={"topics": [{"title": "AI trends"}]},
        error=None, duration_ms=1200,
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
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=1, status="completed",
        config={}, inputs={}, outputs={"v": 1}, error=None, duration_ms=100,
    )
    await store.save_snapshot(
        run_id="run1", agent="topic_generator", version=2, status="completed",
        config={}, inputs={}, outputs={"v": 2}, error=None, duration_ms=200,
    )
    snap = await store.get_snapshot("run1", "topic_generator")
    assert snap["version"] == 2
    assert snap["outputs"]["v"] == 2
    snap_v1 = await store.get_snapshot("run1", "topic_generator", version=1)
    assert snap_v1["version"] == 1
    assert snap_v1["outputs"]["v"] == 1


@pytest.mark.asyncio
async def test_list_snapshots(store: StateStore):
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
    tg = next(s for s in snapshots if s["agent"] == "topic_generator")
    assert tg["version"] == 2


@pytest.mark.asyncio
async def test_list_snapshot_history(store: StateStore):
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
    snap = await store.get_snapshot("nonexistent", "fake_agent")
    assert snap is None


@pytest.mark.asyncio
async def test_save_snapshot_failed_with_error(store: StateStore):
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
