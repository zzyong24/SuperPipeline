"""FastAPI application factory."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import pipelines, contents, runs
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
    app.include_router(sse.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
