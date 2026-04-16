"""API routes for content operations."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from src.api.schemas import ApproveRequest
from src.core.config import load_config
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/contents", tags=["contents"])

def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)

async def _list_contents(status: str | None = None, run_id: str | None = None) -> list[dict]:
    store = _get_store()
    await store.initialize()
    contents = await store.list_contents(status=status, run_id=run_id)
    await store.close()
    return contents

@router.get("")
async def get_contents(status: Optional[str] = None, run_id: Optional[str] = None):
    return await _list_contents(status=status, run_id=run_id)

@router.get("/{content_id}")
async def get_content(content_id: str):
    store = _get_store()
    await store.initialize()
    content = await store.get_content(content_id)
    await store.close()
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    return content

@router.patch("/{content_id}")
async def update_content(content_id: str, body: dict):
    store = _get_store()
    await store.initialize()
    content = await store.get_content(content_id)
    if content is None:
        await store.close()
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    updates = {k: v for k, v in body.items() if k in ("tags", "image_paths", "status", "publish_url")}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    await store.update_content(content_id, **updates)
    await store.close()
    return {"message": "Content updated", "content_id": content_id}


@router.post("/{content_id}/approve")
async def approve_content(content_id: str, body: ApproveRequest):
    store = _get_store()
    await store.initialize()
    content = await store.get_content(content_id)
    if content is None:
        await store.close()
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    updates = {"status": "published"}
    if body.publish_url:
        updates["publish_url"] = body.publish_url
    await store.update_content(content_id, **updates)
    await store.close()
    return {"message": "Content marked as published", "content_id": content_id}
