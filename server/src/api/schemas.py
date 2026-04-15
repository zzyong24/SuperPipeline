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
