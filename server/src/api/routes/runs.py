"""API routes for pipeline run operations."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from src.core.config import load_config
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/runs", tags=["runs"])

def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
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

@router.get("")
async def get_runs(limit: int = 20, status: Optional[str] = None):
    return await _list_runs(limit=limit, status=status)

@router.get("/{run_id}")
async def get_run(run_id: str):
    run = await _get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run
