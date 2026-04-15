"""CLI command: sp agent list / run."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.core.engine import Engine

app = typer.Typer(help="Manage agents")


def _get_engine() -> Engine:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
    pipelines_dir = Path(os.environ.get("SP_PIPELINES_DIR", Path(__file__).parent.parent.parent.parent / "pipelines"))
    config = load_config(config_path)
    return Engine(config, pipelines_dir)


def _list_agents() -> list[dict]:
    engine = _get_engine()
    async def _fetch():
        await engine.initialize()
        agents = engine.registry.list_agents()
        await engine.close()
        return agents
    return asyncio.run(_fetch())


@app.command("list")
def agent_list(
    fmt: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List all registered agents."""
    agents = _list_agents()
    output(agents, fmt, columns=["name", "consumes", "produces", "config_schema"])


@app.command("run")
def agent_run(
    name: str = typer.Argument(help="Agent name to run"),
    input_file: str = typer.Option(..., "--input", "-i", help="Path to input JSON file"),
    config_json: str = typer.Option("{}", "--config", "-c", help="Agent config as JSON string"),
    fmt: str = typer.Option("json", "--format", help="Output format"),
) -> None:
    """Run a single agent (for debugging)."""
    engine = _get_engine()
    async def _run():
        await engine.initialize()
        agent = engine.registry.get(name)
        inputs = json.loads(Path(input_file).read_text())
        config = agent.config_schema.model_validate(json.loads(config_json))
        result = await agent.run(inputs, config)
        await engine.close()
        return result
    try:
        result = asyncio.run(_run())
        output(result, fmt)
    except KeyError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=4)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
