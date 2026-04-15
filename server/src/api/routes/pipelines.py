"""API routes for pipeline operations."""
from __future__ import annotations
import os
from pathlib import Path
from fastapi import APIRouter
from src.core.pipeline_loader import list_pipelines

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])

def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent / "pipelines"

def _list_pipelines() -> list[dict]:
    return list_pipelines(_get_pipelines_dir())

@router.get("")
async def get_pipelines():
    return _list_pipelines()
