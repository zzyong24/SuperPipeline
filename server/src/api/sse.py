"""Server-Sent Events for real-time pipeline status updates."""
from __future__ import annotations
import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["sse"])

_event_queues: dict[str, list[asyncio.Queue]] = {}

def publish_event(run_id: str, event: dict) -> None:
    for queue in _event_queues.get(run_id, []):
        queue.put_nowait(event)

async def _event_stream(run_id: str) -> AsyncGenerator[dict, None]:
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues.setdefault(run_id, []).append(queue)
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield {"event": event.get("type", "update"), "data": json.dumps(event)}
            if event.get("type") == "pipeline_completed":
                break
    except asyncio.TimeoutError:
        yield {"event": "keepalive", "data": "{}"}
    finally:
        _event_queues.get(run_id, []).remove(queue)

@router.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    return EventSourceResponse(_event_stream(run_id))
