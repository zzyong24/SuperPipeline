"""API routes for stage snapshot operations."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.api.schemas import EditSnapshotRequest, RerunStageRequest
from src.core.config import load_config
from src.core.engine import Engine
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/runs/{run_id}/stages", tags=["stages"])

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", _PROJECT_ROOT / "config.yaml"))

def _get_pipelines_dir() -> Path:
    return Path(os.environ.get("SP_PIPELINES_DIR", _PROJECT_ROOT / "pipelines"))

def _get_store() -> StateStore:
    config = load_config(_get_config_path())
    return StateStore(config.storage.database_url)

async def _get_engine() -> Engine:
    config = load_config(_get_config_path())
    engine = Engine(config, _get_pipelines_dir())
    await engine.initialize()
    return engine


@router.get("")
async def list_stages(run_id: str):
    """列出某次运行所有节点的最新快照。"""
    store = _get_store()
    await store.initialize()
    snapshots = await store.list_snapshots(run_id)
    await store.close()
    if not snapshots:
        # Check if run exists
        run = await _check_run_exists(run_id)
    return snapshots


@router.get("/{agent}")
async def get_stage(run_id: str, agent: str, version: int | None = None):
    """查看某节点快照详情。"""
    store = _get_store()
    await store.initialize()
    snap = await store.get_snapshot(run_id, agent, version=version)
    await store.close()
    if snap is None:
        raise HTTPException(status_code=404, detail=f"节点 '{agent}' 在运行 '{run_id}' 中未找到快照")
    return snap


@router.put("/{agent}")
async def edit_stage_outputs(run_id: str, agent: str, body: EditSnapshotRequest):
    """编辑某节点的输出数据。"""
    store = _get_store()
    await store.initialize()
    # Get latest snapshot to find its version
    snap = await store.get_snapshot(run_id, agent)
    if snap is None:
        await store.close()
        raise HTTPException(status_code=404, detail=f"节点 '{agent}' 在运行 '{run_id}' 中未找到快照")
    await store.update_snapshot_outputs(run_id, agent, snap["version"], body.outputs)
    # Return updated snapshot
    updated = await store.get_snapshot(run_id, agent, version=snap["version"])
    await store.close()
    return updated


@router.post("/{agent}/rerun")
async def rerun_stage(run_id: str, agent: str, body: RerunStageRequest):
    """从某节点开始重跑（默认级联）。"""
    engine = await _get_engine()
    try:
        result = await engine.rerun_from_stage(
            run_id=run_id,
            from_agent=agent,
            config_overrides=body.config if body.config else None,
            model_override=body.model,
            prompt_override=body.prompt,
            only=body.only,
        )
        return {"status": result.get("stage", "completed"), "run_id": run_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        await engine.close()


@router.get("/{agent}/history")
async def get_stage_history(run_id: str, agent: str):
    """查看某节点的所有版本历史。"""
    store = _get_store()
    await store.initialize()
    history = await store.list_snapshot_history(run_id, agent)
    await store.close()
    return history


async def _check_run_exists(run_id: str):
    store = _get_store()
    await store.initialize()
    run = await store.get_run(run_id)
    await store.close()
    if run is None:
        raise HTTPException(status_code=404, detail=f"运行 '{run_id}' 不存在")
    return run
