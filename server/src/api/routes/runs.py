"""API routes for pipeline run operations."""
from __future__ import annotations
import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from src.api.schemas import RunPipelineRequest, RunPipelineResponse
from src.core.config import load_config
from src.core.engine import Engine
from src.core.state import UserBrief
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/runs", tags=["runs"])

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", _PROJECT_ROOT / "config.yaml"))

def _get_pipelines_dir() -> Path:
    return Path(os.environ.get("SP_PIPELINES_DIR", _PROJECT_ROOT / "pipelines"))

def _get_store() -> StateStore:
    config = load_config(_get_config_path())
    return StateStore(config.storage.db_path)

async def _list_runs(limit: int = 20, status: str | None = None) -> list[dict]:
    store = _get_store()
    await store.initialize()
    runs = await store.list_runs(limit=limit, status=status)
    await store.close()
    return runs

async def _get_run(run_id: str) -> dict | None:
    store = _get_store()
    await store.initialize()
    run = await store.get_run(run_id)
    await store.close()
    return run

async def _execute_pipeline_bg(run_id: str, pipeline_name: str, brief: UserBrief, stage_overrides: dict[str, dict] | None = None) -> None:
    """Execute pipeline in background task."""
    config = load_config(_get_config_path())
    engine = Engine(config, _get_pipelines_dir())
    try:
        await engine.initialize()
        pipeline_config = engine.load_pipeline(pipeline_name)
        await engine.state_store.update_run(run_id, status="running", state={})
        result = await engine.orchestrator.run(pipeline_config, brief, run_id=run_id, stage_overrides=stage_overrides)
        # Save contents to DB
        for platform, content_data in result.get("contents", {}).items():
            content_id = f"{run_id}-{platform}"
            review = result.get("reviews", {}).get(platform, {})
            status = "approved" if review.get("passed", False) else "pending_review"
            await engine.state_store.save_content(
                content_id=content_id, run_id=run_id, platform=platform,
                title=content_data.get("title", ""), body=content_data.get("body", ""),
                status=status, tags=content_data.get("tags", []),
                image_paths=content_data.get("image_paths", []),
            )
        await engine.state_store.update_run(run_id, status=result.get("stage", "completed"), state=result)
    except Exception as e:
        store = _get_store()
        await store.initialize()
        await store.update_run(run_id, status="failed", state={"error": str(e)})
        await store.close()
    finally:
        await engine.close()

@router.get("")
async def get_runs(limit: int = 20, status: Optional[str] = None):
    return await _list_runs(limit=limit, status=status)

@router.post("", response_model=RunPipelineResponse)
async def create_run(body: RunPipelineRequest):
    """Trigger a new pipeline run. Returns immediately, executes in background."""
    run_id = uuid.uuid4().hex[:12]
    brief = UserBrief(
        topic=body.brief,
        keywords=body.keywords,
        platform_hints=body.platform_hints,
    )
    # Resolve display name from YAML
    from src.core.pipeline_loader import load_pipeline as _load_pl
    yaml_file = _get_pipelines_dir() / f"{body.pipeline}.yaml"
    if not yaml_file.exists():
        raise HTTPException(status_code=404, detail=f"管道 '{body.pipeline}' 不存在")
    pl_config = _load_pl(yaml_file)
    display_name = pl_config.name  # Chinese name from YAML

    # Save run record immediately
    store = _get_store()
    await store.initialize()
    await store.save_run(run_id, display_name, "pending", {})
    await store.close()
    # Fire and forget background execution
    asyncio.create_task(_execute_pipeline_bg(run_id, body.pipeline, brief, stage_overrides=body.stage_overrides))
    return RunPipelineResponse(run_id=run_id, status="pending")

@router.get("/{run_id}")
async def get_run(run_id: str):
    run = await _get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run
