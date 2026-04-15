"""API routes for pipeline operations."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from src.core.pipeline_loader import list_pipelines, load_pipeline

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent.parent / "pipelines"

def _list_pipelines() -> list[dict]:
    return list_pipelines(_get_pipelines_dir())

@router.get("")
async def get_pipelines():
    return _list_pipelines()

@router.get("/{name}")
async def get_pipeline(name: str):
    """Return full pipeline config including all stage configs."""
    pipelines_dir = _get_pipelines_dir()
    yaml_file = pipelines_dir / f"{name}.yaml"
    if not yaml_file.exists():
        raise HTTPException(status_code=404, detail=f"Pipeline '{name}' not found")
    config = load_pipeline(yaml_file)
    return config.model_dump()
