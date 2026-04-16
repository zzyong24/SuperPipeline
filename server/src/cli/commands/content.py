"""CLI command: sp content list / get / approve."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer

from src.cli.formatters import output, console
from src.core.config import load_config
from src.storage.state_store import StateStore

app = typer.Typer(help="Manage generated content")


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.database_url)


def _list_contents(status: str | None = None, run_id: str | None = None) -> list[dict]:
    store = _get_store()
    async def _fetch():
        await store.initialize()
        contents = await store.list_contents(status=status, run_id=run_id)
        await store.close()
        return contents
    return asyncio.run(_fetch())


def _get_content(content_id: str) -> dict | None:
    store = _get_store()
    async def _fetch():
        await store.initialize()
        content = await store.get_content(content_id)
        await store.close()
        return content
    return asyncio.run(_fetch())


def _update_content(content_id: str, **kwargs) -> None:
    store = _get_store()
    async def _update():
        await store.initialize()
        await store.update_content(content_id, **kwargs)
        await store.close()
    asyncio.run(_update())


@app.command("list")
def content_list(
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status"),
    run: Optional[str] = typer.Option(None, "--run", help="Filter by run ID"),
    fmt: str = typer.Option("table", "--format", help="Output format"),
) -> None:
    """List generated content."""
    contents = _list_contents(status=status, run_id=run)
    output(contents, fmt, columns=["content_id", "platform", "title", "status", "created_at"])


@app.command("get")
def content_get(
    content_id: str = typer.Argument(help="Content ID"),
    fmt: str = typer.Option("json", "--format", help="Output format"),
    copy: bool = typer.Option(False, "--copy", help="Output plain text for copying"),
) -> None:
    """Get content details."""
    content = _get_content(content_id)
    if content is None:
        typer.echo(f"Content '{content_id}' not found", err=True)
        raise typer.Exit(code=4)

    if copy:
        console.print(f"{content.get('title', '')}\n")
        console.print(content.get("body", ""))
        tags = content.get("tags", [])
        if tags:
            console.print(f"\n{'  '.join(f'#{t}' for t in tags)}")
    else:
        output(content, fmt)


@app.command("approve")
def content_approve(
    content_id: str = typer.Argument(help="Content ID"),
    publish_url: str = typer.Option("", "--publish-url", help="URL where content was published"),
) -> None:
    """Mark content as published."""
    content = _get_content(content_id)
    if content is None:
        typer.echo(f"Content '{content_id}' not found", err=True)
        raise typer.Exit(code=4)
    updates = {"status": "published"}
    if publish_url:
        updates["publish_url"] = publish_url
    _update_content(content_id, **updates)
    typer.echo(f"Content '{content_id}' marked as published")
