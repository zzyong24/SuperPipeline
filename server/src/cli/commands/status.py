"""CLI command: sp status [run_id]."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.storage.state_store import StateStore


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.database_url)


def _get_run_status(limit: int = 20) -> list[dict]:
    store = _get_store()
    async def _fetch():
        await store.initialize()
        runs = await store.list_runs(limit=limit)
        await store.close()
        return runs
    return asyncio.run(_fetch())


def _get_run_detail(run_id: str) -> dict | None:
    store = _get_store()
    async def _fetch():
        await store.initialize()
        run = await store.get_run(run_id)
        await store.close()
        return run
    return asyncio.run(_fetch())


def status_command(
    run_id: Optional[str] = typer.Argument(None, help="Specific run ID to check"),
    fmt: str = typer.Option("table", "--format", help="Output format"),
    stage: Optional[str] = typer.Option(None, "--stage", help="Show specific stage details"),
) -> None:
    """Check pipeline run status."""
    if run_id:
        run = _get_run_detail(run_id)
        if run is None:
            typer.echo(f"Run '{run_id}' not found", err=True)
            raise typer.Exit(code=4)
        if stage and "state" in run:
            state = run.get("state", {})
            output({"stage": stage, "data": state.get(stage, "No data for this stage")}, fmt)
        else:
            output(run, fmt)
    else:
        runs = _get_run_status()
        output(runs, fmt, columns=["run_id", "pipeline_name", "status", "created_at"])
