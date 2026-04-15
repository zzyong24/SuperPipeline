"""CLI commands for managing pipeline configurations."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from src.cli.formatters import output
from src.core.pipeline_loader import list_pipelines, load_pipeline

app = typer.Typer(help="Manage pipeline configurations")


def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent.parent / "pipelines"


@app.command("list")
def pipeline_list(
    fmt: str = typer.Option("table", "--format", help="Output format: json, table, plain"),
) -> None:
    """List all available pipeline configurations."""
    pipelines_dir = _get_pipelines_dir()
    if not pipelines_dir.exists():
        typer.echo("No pipelines directory found", err=True)
        raise typer.Exit(code=1)
    pipelines = list_pipelines(pipelines_dir)
    output(pipelines, fmt, columns=["name", "description", "platforms", "stages", "file"])


@app.command("show")
def pipeline_show(
    name: str = typer.Argument(help="Pipeline file name (without .yaml)"),
    fmt: str = typer.Option("plain", "--format", help="Output format: json, plain"),
) -> None:
    """Show details of a pipeline configuration."""
    pipelines_dir = _get_pipelines_dir()
    yaml_file = pipelines_dir / f"{name}.yaml"
    if not yaml_file.exists():
        typer.echo(f"Pipeline '{name}' not found", err=True)
        raise typer.Exit(code=4)
    config = load_pipeline(yaml_file)
    output(config.model_dump(), fmt)
