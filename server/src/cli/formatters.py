"""Output formatters for CLI commands."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def output(data: Any, fmt: str = "table", columns: list[str] | None = None) -> None:
    if fmt == "json":
        console.print_json(json.dumps(data, ensure_ascii=False, default=str))
    elif fmt == "table" and isinstance(data, list) and data:
        table = Table()
        cols = columns or list(data[0].keys())
        for col in cols:
            table.add_column(col)
        for row in data:
            table.add_row(*[str(row.get(c, "")) for c in cols])
        console.print(table)
    elif fmt == "plain":
        if isinstance(data, str):
            console.print(data)
        else:
            console.print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        console.print(data)
