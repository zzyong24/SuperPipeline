"""CLI command: sp run <pipeline> --brief "..."."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.core.engine import Engine
from src.core.state import UserBrief


def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))


def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent / "pipelines"


def _run_pipeline(pipeline_name: str, brief_text: str) -> dict:
    config = load_config(_get_config_path())
    engine = Engine(config, _get_pipelines_dir())

    async def _execute():
        await engine.initialize()
        brief = UserBrief(topic=brief_text)
        result = await engine.run_pipeline(pipeline_name, brief)
        await engine.close()
        return result

    return asyncio.run(_execute())


def run_command(
    pipeline: str = typer.Argument(help="Pipeline name"),
    brief: str = typer.Option("", "--brief", "-b", help="Topic/brief text"),
    brief_file: str = typer.Option("", "--brief-file", help="Path to brief JSON file"),
    fmt: str = typer.Option("table", "--format", help="Output format"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for completion"),
) -> None:
    """Run a content production pipeline."""
    if not brief and not brief_file:
        typer.echo("Error: Provide --brief or --brief-file", err=True)
        raise typer.Exit(code=2)

    brief_text = brief
    if brief_file:
        brief_data = json.loads(Path(brief_file).read_text())
        brief_text = brief_data.get("topic", brief_data.get("brief", ""))

    try:
        result = _run_pipeline(pipeline, brief_text)
        output({"run_id": result["run_id"], "status": result["status"]}, fmt)
        raise typer.Exit(code=0 if result["status"] == "completed" else 3)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=4)
