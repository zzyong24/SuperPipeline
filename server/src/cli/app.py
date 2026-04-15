"""SuperPipeline CLI — main entry point."""

from __future__ import annotations

import typer

from src.cli.commands import pipeline as pipeline_cmd
from src.cli.commands.run import run_command
from src.cli.commands.status import status_command
from src.cli.commands import content as content_cmd
from src.cli.commands import agent as agent_cmd

app = typer.Typer(
    name="sp",
    help="SuperPipeline — Multi-agent content production pipeline",
    no_args_is_help=True,
)

app.add_typer(pipeline_cmd.app, name="pipeline")
app.command("run")(run_command)
app.command("status")(status_command)
app.add_typer(content_cmd.app, name="content")
app.add_typer(agent_cmd.app, name="agent")


if __name__ == "__main__":
    app()
