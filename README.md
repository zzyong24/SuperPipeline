# SuperPipeline

Multi-agent content production pipeline. Automates topic → material → generation → review → analytics.

## Quick Start

```bash
# Install
cd server && pip install -e ".[dev]"

# Configure
cp config.yaml config.yaml.bak  # edit API keys in config.yaml

# Run a pipeline
sp run xiaohongshu_image_text --brief "AI编程工具测评"

# Check status
sp status

# Get content
sp content list
sp content get <content_id> --copy
```

## CLI Reference

```bash
sp run <pipeline> --brief "..."     # Run pipeline
sp status [run_id]                  # Check status
sp content list [--status approved] # List content
sp content get <id> [--copy]        # Get content
sp content approve <id>             # Mark published
sp pipeline list                    # List pipelines
sp agent list                       # List agents
```

All commands support `--format json` for machine-readable output.

## Architecture

See `docs/architecture.md`

## Adding Agents

See `docs/agent-dev-guide.md`

## Web UI

```bash
cd web && npm install && npm run dev
```

Opens at http://localhost:3000 — read-only dashboard for checking status and copying content.
