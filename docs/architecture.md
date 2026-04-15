# SuperPipeline Architecture

## Core Concept
YAML-configured pipeline → LangGraph graph → Agent nodes → shared State.

## Directory Map
- `server/src/core/` — engine, orchestrator, registry, config, model adapters
- `server/src/agents/` — one dir per agent, each self-contained
- `server/src/platforms/` — platform rule adapters
- `server/src/cli/` — Typer CLI (primary interface)
- `server/src/api/` — FastAPI (for Web UI)
- `server/src/storage/` — SQLite + file storage
- `server/pipelines/` — YAML pipeline configs
- `web/` — Next.js dashboard (read-only)

## Data Flow
1. User/Agent triggers `sp run <pipeline> --brief "topic"`
2. Engine loads YAML → builds LangGraph → runs agents sequentially
3. Each agent reads from State, writes to State
4. Results saved to SQLite + file system
5. CLI or Web UI reads results

## Adding a New Agent
See `docs/agent-dev-guide.md`

## Adding a New Platform
1. Create `server/src/platforms/my_platform.py`
2. Implement `BasePlatform` with `validate()` and `format_content()`
3. Use `@register_platform` decorator
4. Add to pipeline YAML
