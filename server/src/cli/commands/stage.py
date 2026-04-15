"""CLI commands: sp stage list / show / edit / rerun / history."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.core.engine import Engine
from src.storage.state_store import StateStore

app = typer.Typer(help="管理管道节点快照")

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", _PROJECT_ROOT / "config.yaml"))


def _get_pipelines_dir() -> Path:
    return Path(os.environ.get("SP_PIPELINES_DIR", _PROJECT_ROOT / "pipelines"))


def _get_store() -> StateStore:
    config = load_config(_get_config_path())
    return StateStore(config.storage.db_path)


def _get_engine() -> Engine:
    config = load_config(_get_config_path())
    return Engine(config, _get_pipelines_dir())


@app.command("list")
def stage_list(
    run_id: str = typer.Argument(help="运行 ID"),
    fmt: str = typer.Option("table", "--format", help="输出格式: json, table, plain"),
) -> None:
    """列出某次运行所有节点的最新快照。"""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        snapshots = await store.list_snapshots(run_id)
        await store.close()
        return snapshots

    snapshots = asyncio.run(_fetch())
    if not snapshots:
        typer.echo(f"运行 '{run_id}' 没有找到节点快照", err=True)
        raise typer.Exit(code=4)

    table_data = []
    for s in snapshots:
        table_data.append({
            "agent": s["agent"],
            "version": s["version"],
            "status": s["status"],
            "duration_ms": s.get("duration_ms", 0),
            "output_preview": _preview(s.get("outputs")),
        })
    output(table_data, fmt, columns=["agent", "version", "status", "duration_ms", "output_preview"])


@app.command("show")
def stage_show(
    run_id: str = typer.Argument(help="运行 ID"),
    agent: str = typer.Argument(help="节点名称"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="指定版本号"),
    field: Optional[str] = typer.Option(None, "--field", "-f", help="只显示某个字段 (如 outputs.contents)"),
    fmt: str = typer.Option("json", "--format", help="输出格式"),
) -> None:
    """查看某节点快照的完整详情。"""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        snap = await store.get_snapshot(run_id, agent, version=version)
        await store.close()
        return snap

    snap = asyncio.run(_fetch())
    if snap is None:
        typer.echo(f"节点 '{agent}' 在运行 '{run_id}' 中未找到快照", err=True)
        raise typer.Exit(code=4)

    if field:
        # Navigate nested fields: "outputs.contents.xiaohongshu"
        data = snap
        for part in field.split("."):
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                typer.echo(f"字段 '{field}' 不存在", err=True)
                raise typer.Exit(code=4)
        output(data, fmt)
    else:
        output(snap, fmt)


@app.command("edit")
def stage_edit(
    run_id: str = typer.Argument(help="运行 ID"),
    agent: str = typer.Argument(help="节点名称"),
    set_field: Optional[str] = typer.Option(None, "--set", help="设置字段值: 'outputs.title=新标题'"),
    file: Optional[str] = typer.Option(None, "--file", help="从文件加载完整输出 JSON"),
    value: Optional[str] = typer.Option(None, "--value", help="直接传入完整输出 JSON 字符串"),
    fmt: str = typer.Option("json", "--format", help="输出格式"),
) -> None:
    """编辑某节点的输出数据。"""
    store = _get_store()

    async def _do_edit():
        await store.initialize()
        snap = await store.get_snapshot(run_id, agent)
        if snap is None:
            await store.close()
            typer.echo(f"节点 '{agent}' 在运行 '{run_id}' 中未找到快照", err=True)
            raise typer.Exit(code=4)

        outputs = snap.get("outputs") or {}

        if file:
            outputs = json.loads(Path(file).read_text())
        elif value:
            outputs = json.loads(value)
        elif set_field:
            # Parse "key.subkey=value"
            if "=" not in set_field:
                typer.echo("--set 格式: 'key.subkey=value'", err=True)
                raise typer.Exit(code=2)
            path, val = set_field.split("=", 1)
            parts = path.split(".")
            # Navigate to parent
            target = outputs
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            # Try to parse as JSON, fallback to string
            try:
                target[parts[-1]] = json.loads(val)
            except (json.JSONDecodeError, ValueError):
                target[parts[-1]] = val
        else:
            typer.echo("请提供 --set, --file, 或 --value 参数", err=True)
            raise typer.Exit(code=2)

        await store.update_snapshot_outputs(run_id, agent, snap["version"], outputs)
        updated = await store.get_snapshot(run_id, agent, version=snap["version"])
        await store.close()
        return updated

    result = asyncio.run(_do_edit())
    output(result, fmt)


@app.command("rerun")
def stage_rerun(
    run_id: str = typer.Argument(help="运行 ID"),
    agent: str = typer.Argument(help="从哪个节点开始重跑"),
    config_json: str = typer.Option("{}", "--config", "-c", help="覆盖节点配置 (JSON)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="覆盖模型名称"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="覆盖提示词"),
    prompt_file: Optional[str] = typer.Option(None, "--prompt-file", help="从文件读取提示词"),
    only: bool = typer.Option(False, "--only", help="只重跑此节点，不级联"),
    fmt: str = typer.Option("json", "--format", help="输出格式"),
) -> None:
    """从某节点开始级联重跑。"""
    engine = _get_engine()

    # Resolve prompt
    effective_prompt = prompt
    if prompt_file:
        effective_prompt = Path(prompt_file).read_text()

    # Parse config
    try:
        config_overrides = json.loads(config_json)
    except json.JSONDecodeError:
        typer.echo("--config 不是有效的 JSON", err=True)
        raise typer.Exit(code=2)

    async def _do_rerun():
        await engine.initialize()
        try:
            result = await engine.rerun_from_stage(
                run_id=run_id,
                from_agent=agent,
                config_overrides=config_overrides if config_overrides else None,
                model_override=model,
                prompt_override=effective_prompt,
                only=only,
            )
            return {"status": result.get("stage", "completed"), "run_id": run_id}
        except ValueError as e:
            typer.echo(f"错误: {e}", err=True)
            raise typer.Exit(code=4)
        finally:
            await engine.close()

    result = asyncio.run(_do_rerun())
    output(result, fmt)


@app.command("history")
def stage_history(
    run_id: str = typer.Argument(help="运行 ID"),
    agent: str = typer.Argument(help="节点名称"),
    fmt: str = typer.Option("table", "--format", help="输出格式"),
) -> None:
    """查看某节点的所有版本历史。"""
    store = _get_store()

    async def _fetch():
        await store.initialize()
        history = await store.list_snapshot_history(run_id, agent)
        await store.close()
        return history

    history = asyncio.run(_fetch())
    if not history:
        typer.echo(f"节点 '{agent}' 在运行 '{run_id}' 中没有历史记录", err=True)
        raise typer.Exit(code=4)

    table_data = []
    for h in history:
        table_data.append({
            "version": h["version"],
            "status": h["status"],
            "duration_ms": h.get("duration_ms", 0),
            "created_at": h.get("created_at", ""),
        })
    output(table_data, fmt, columns=["version", "status", "duration_ms", "created_at"])


def _preview(data, max_len: int = 80) -> str:
    """Create a short preview string from output data."""
    if data is None:
        return "(无输出)"
    s = json.dumps(data, ensure_ascii=False)
    return s[:max_len] + "..." if len(s) > max_len else s
