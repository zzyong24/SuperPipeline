"""PostgreSQL-backed storage for pipeline runs and content records."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import asyncpg


class StateStore:
    """Async PostgreSQL store for pipeline metadata."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        self._pool = await asyncpg.create_pool(self.database_url, min_size=2, max_size=10)
        async with self._pool.acquire() as conn:
            await conn.execute("""
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
                    id SERIAL PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    metrics_json TEXT DEFAULT '{}',
                    insights_json TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stage_snapshots (
                    id SERIAL PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL DEFAULT '{}',
                    inputs_json TEXT NOT NULL DEFAULT '{}',
                    outputs_json TEXT,
                    error TEXT,
                    duration_ms INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, agent, version)
                );
            """)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_to_dict(self, row: asyncpg.Record) -> dict:
        return dict(row)

    # ── Pipeline Runs ─────────────────────────────────────────────────

    async def save_run(self, run_id: str, pipeline_name: str, status: str, state: dict) -> None:
        now = self._now()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO pipeline_runs (run_id, pipeline_name, status, state_json, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6)",
                run_id, pipeline_name, status, json.dumps(state), now, now,
            )

    async def update_run(self, run_id: str, status: str | None = None, state: dict | None = None) -> None:
        updates = []
        params = []
        idx = 1
        if status is not None:
            updates.append(f"status = ${idx}")
            params.append(status)
            idx += 1
        if state is not None:
            updates.append(f"state_json = ${idx}")
            params.append(json.dumps(state))
            idx += 1
        updates.append(f"updated_at = ${idx}")
        params.append(self._now())
        idx += 1
        params.append(run_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE pipeline_runs SET {', '.join(updates)} WHERE run_id = ${idx}",
                *params,
            )

    async def get_run(self, run_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM pipeline_runs WHERE run_id = $1", run_id)
        if row is None:
            return None
        d = self._row_to_dict(row)
        d["state"] = json.loads(d["state_json"])
        return d

    async def list_runs(self, limit: int = 20, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM pipeline_runs"
        params: list = []
        idx = 1
        if status:
            query += f" WHERE status = ${idx}"
            params.append(status)
            idx += 1
        query += f" ORDER BY created_at DESC LIMIT ${idx}"
        params.append(limit)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [{**self._row_to_dict(r), "state": json.loads(r["state_json"])} for r in rows]

    # ── Contents ──────────────────────────────────────────────────────

    async def save_content(
        self, content_id: str, run_id: str, platform: str, title: str, body: str, status: str = "pending_review",
        tags: list[str] | None = None, image_paths: list[str] | None = None,
    ) -> None:
        now = self._now()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO contents (content_id, run_id, platform, title, body, tags_json, image_paths_json, status, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                content_id, run_id, platform, title, body, json.dumps(tags or []), json.dumps(image_paths or []), status, now, now,
            )

    async def get_content(self, content_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM contents WHERE content_id = $1", content_id)
        if row is None:
            return None
        result = self._row_to_dict(row)
        result["tags"] = json.loads(result.pop("tags_json"))
        result["image_paths"] = json.loads(result.pop("image_paths_json"))
        return result

    async def list_contents(self, run_id: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
        query = "SELECT * FROM contents WHERE 1=1"
        params: list = []
        idx = 1
        if run_id:
            query += f" AND run_id = ${idx}"
            params.append(run_id)
            idx += 1
        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1
        query += f" ORDER BY created_at DESC LIMIT ${idx}"
        params.append(limit)
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        results = []
        for r in rows:
            d = self._row_to_dict(r)
            d["tags"] = json.loads(d.pop("tags_json"))
            d["image_paths"] = json.loads(d.pop("image_paths_json"))
            results.append(d)
        return results

    async def update_content(self, content_id: str, **kwargs) -> None:
        updates = []
        params = []
        idx = 1
        for key, value in kwargs.items():
            if key in ("tags", "image_paths"):
                updates.append(f"{key}_json = ${idx}")
                params.append(json.dumps(value))
            else:
                updates.append(f"{key} = ${idx}")
                params.append(value)
            idx += 1
        updates.append(f"updated_at = ${idx}")
        params.append(self._now())
        idx += 1
        params.append(content_id)
        async with self._pool.acquire() as conn:
            await conn.execute(
                f"UPDATE contents SET {', '.join(updates)} WHERE content_id = ${idx}",
                *params,
            )

    # ── Stage Snapshots ───────────────────────────────────────────────

    def _parse_snapshot_row(self, row) -> dict:
        d = self._row_to_dict(row)
        d["config"] = json.loads(d.pop("config_json"))
        d["inputs"] = json.loads(d.pop("inputs_json"))
        outputs_raw = d.pop("outputs_json")
        d["outputs"] = json.loads(outputs_raw) if outputs_raw is not None else None
        return d

    async def save_snapshot(
        self, run_id: str, agent: str, version: int, status: str,
        config: dict, inputs: dict, outputs: dict | None,
        error: str | None, duration_ms: int | None,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO stage_snapshots
                   (run_id, agent, version, status, config_json, inputs_json, outputs_json, error, duration_ms, created_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                run_id, agent, version, status,
                json.dumps(config, ensure_ascii=False),
                json.dumps(inputs, ensure_ascii=False),
                json.dumps(outputs, ensure_ascii=False) if outputs is not None else None,
                error, duration_ms, self._now(),
            )

    async def get_snapshot(self, run_id: str, agent: str, version: int | None = None) -> dict | None:
        async with self._pool.acquire() as conn:
            if version is not None:
                row = await conn.fetchrow(
                    "SELECT * FROM stage_snapshots WHERE run_id = $1 AND agent = $2 AND version = $3",
                    run_id, agent, version,
                )
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM stage_snapshots WHERE run_id = $1 AND agent = $2 ORDER BY version DESC LIMIT 1",
                    run_id, agent,
                )
        if row is None:
            return None
        return self._parse_snapshot_row(row)

    async def list_snapshots(self, run_id: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT s.* FROM stage_snapshots s
                   INNER JOIN (
                       SELECT run_id, agent, MAX(version) as max_v
                       FROM stage_snapshots WHERE run_id = $1
                       GROUP BY run_id, agent
                   ) latest ON s.run_id = latest.run_id AND s.agent = latest.agent AND s.version = latest.max_v
                   ORDER BY s.id""",
                run_id,
            )
        return [self._parse_snapshot_row(r) for r in rows]

    async def list_snapshot_history(self, run_id: str, agent: str) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM stage_snapshots WHERE run_id = $1 AND agent = $2 ORDER BY version ASC",
                run_id, agent,
            )
        return [self._parse_snapshot_row(r) for r in rows]

    async def update_snapshot_outputs(self, run_id: str, agent: str, version: int, outputs: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE stage_snapshots SET outputs_json = $1 WHERE run_id = $2 AND agent = $3 AND version = $4",
                json.dumps(outputs, ensure_ascii=False), run_id, agent, version,
            )

    async def get_next_version(self, run_id: str, agent: str) -> int:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT MAX(version) as max_v FROM stage_snapshots WHERE run_id = $1 AND agent = $2",
                run_id, agent,
            )
        max_v = row["max_v"] if row and row["max_v"] is not None else 0
        return max_v + 1
