"""SQLite-backed storage for pipeline runs and content records."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite


class StateStore:
    """Async SQLite store for pipeline metadata."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                pipeline_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                state_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS contents (
                content_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                tags_json TEXT DEFAULT '[]',
                image_paths_json TEXT DEFAULT '[]',
                review_score REAL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'pending_review',
                publish_url TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id TEXT NOT NULL,
                metrics_json TEXT DEFAULT '{}',
                insights_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );
        """)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def save_run(self, run_id: str, pipeline_name: str, status: str, state: dict) -> None:
        now = self._now()
        await self._db.execute(
            "INSERT INTO pipeline_runs (run_id, pipeline_name, status, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, pipeline_name, status, json.dumps(state), now, now),
        )
        await self._db.commit()

    async def update_run(self, run_id: str, status: str | None = None, state: dict | None = None) -> None:
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if state is not None:
            updates.append("state_json = ?")
            params.append(json.dumps(state))
        updates.append("updated_at = ?")
        params.append(self._now())
        params.append(run_id)
        await self._db.execute(
            f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = ?",
            params,
        )
        await self._db.commit()

    async def get_run(self, run_id: str) -> dict | None:
        cursor = await self._db.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return {**dict(row), "state": json.loads(row["state_json"])}

    async def list_runs(self, limit: int = 20, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM pipeline_runs"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        return [{**dict(r), "state": json.loads(r["state_json"])} for r in rows]

    async def save_content(
        self, content_id: str, run_id: str, platform: str, title: str, body: str, status: str = "pending_review",
        tags: list[str] | None = None, image_paths: list[str] | None = None,
    ) -> None:
        now = self._now()
        await self._db.execute(
            "INSERT INTO contents (content_id, run_id, platform, title, body, tags_json, image_paths_json, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (content_id, run_id, platform, title, body, json.dumps(tags or []), json.dumps(image_paths or []), status, now, now),
        )
        await self._db.commit()

    async def get_content(self, content_id: str) -> dict | None:
        cursor = await self._db.execute("SELECT * FROM contents WHERE content_id = ?", (content_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        result["tags"] = json.loads(result.pop("tags_json"))
        result["image_paths"] = json.loads(result.pop("image_paths_json"))
        return result

    async def list_contents(self, run_id: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM contents WHERE 1=1"
        params: list = []
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cursor = await self._db.execute(query, params)
        rows = await cursor.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["tags"] = json.loads(d.pop("tags_json"))
            d["image_paths"] = json.loads(d.pop("image_paths_json"))
            results.append(d)
        return results

    async def update_content(self, content_id: str, **kwargs) -> None:
        updates = []
        params = []
        for key, value in kwargs.items():
            if key in ("tags", "image_paths"):
                updates.append(f"{key}_json = ?")
                params.append(json.dumps(value))
            else:
                updates.append(f"{key} = ?")
                params.append(value)
        updates.append("updated_at = ?")
        params.append(self._now())
        params.append(content_id)
        await self._db.execute(
            f"UPDATE contents SET {', '.join(updates)} WHERE content_id = ?",
            params,
        )
        await self._db.commit()
