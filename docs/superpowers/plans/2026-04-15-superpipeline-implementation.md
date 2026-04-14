# SuperPipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-Agent content production pipeline that automates topic generation, material collection, content creation, review, and analytics — driven via CLI, viewable via lightweight Web UI.

**Architecture:** LangGraph-based orchestrator reads YAML pipeline configs, dynamically assembles Agent nodes into a StateGraph. Each Agent is a self-contained module with declared inputs/outputs. CLI (Typer) is the primary interface; FastAPI + SSE serves a read-only Next.js dashboard.

**Tech Stack:** Python 3.12+, LangGraph, Typer, FastAPI, SQLite (via aiosqlite), Jinja2, Pydantic v2, MiniMax API (OpenAI-compatible), Next.js 15 (App Router)

---

## Phase 1: Project Bootstrap + Core Engine

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `server/pyproject.toml`
- Create: `server/src/__init__.py`
- Create: `server/src/core/__init__.py`
- Create: `server/src/agents/__init__.py`
- Create: `server/src/platforms/__init__.py`
- Create: `server/src/cli/__init__.py`
- Create: `server/src/api/__init__.py`
- Create: `server/src/storage/__init__.py`
- Create: `server/config.yaml`
- Create: `.gitignore`

- [ ] **Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "superpipeline"
version = "0.1.0"
description = "Multi-agent content production pipeline"
requires-python = ">=3.12"
dependencies = [
    "langgraph>=0.4.0",
    "langgraph-checkpoint-sqlite>=2.0.0",
    "pydantic>=2.0.0",
    "typer[all]>=0.12.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "aiosqlite>=0.20.0",
    "httpx>=0.27.0",
    "jinja2>=3.1.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "sse-starlette>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.5.0",
]

[project.scripts]
sp = "src.cli.app:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 100
```

- [ ] **Step 2: Create .gitignore**

```
data/
*.db
__pycache__/
.venv/
.env
*.pyc
dist/
*.egg-info/
.ruff_cache/
.pytest_cache/
node_modules/
.next/
```

- [ ] **Step 3: Create config.yaml**

```yaml
models:
  text:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-chat"
    max_tokens: 4096
  image:
    provider: minimax
    api_key: ${MINIMAX_API_KEY}
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-image"

storage:
  db_path: "data/superpipeline.db"
  assets_dir: "data/assets"
  outputs_dir: "data/outputs"

server:
  host: "0.0.0.0"
  port: 8000
```

- [ ] **Step 4: Create all __init__.py files and directory structure**

```bash
mkdir -p server/src/{core,agents,platforms,cli/commands,api/routes,storage}
mkdir -p server/pipelines server/prompts/{styles,platforms}
mkdir -p server/tests/{agents,integration}
mkdir -p data/{assets,outputs}
touch server/src/__init__.py
touch server/src/core/__init__.py
touch server/src/agents/__init__.py
touch server/src/platforms/__init__.py
touch server/src/cli/__init__.py
touch server/src/cli/commands/__init__.py
touch server/src/api/__init__.py
touch server/src/api/routes/__init__.py
touch server/src/storage/__init__.py
touch server/tests/__init__.py
touch server/tests/agents/__init__.py
touch server/tests/integration/__init__.py
```

- [ ] **Step 5: Install dependencies**

Run: `cd server && pip install -e ".[dev]"`
Expected: Successful installation, `sp --help` shows Typer default help

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding with dependencies and config"
```

---

### Task 2: PipelineState and data models

**Files:**
- Create: `server/src/core/state.py`
- Create: `server/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_state.py
import pytest
from src.core.state import (
    UserBrief,
    Topic,
    Material,
    PlatformContent,
    ReviewResult,
    PipelineError,
    PipelineState,
)


def test_user_brief_creation():
    brief = UserBrief(topic="AI tools review", keywords=["AI", "coding"], platform_hints=["xiaohongshu"])
    assert brief.topic == "AI tools review"
    assert len(brief.keywords) == 2


def test_topic_creation():
    topic = Topic(title="Top 5 AI Coding Tools", angle="comparison", score=8.5)
    assert topic.title == "Top 5 AI Coding Tools"
    assert topic.score == 8.5


def test_platform_content_creation():
    content = PlatformContent(
        platform="xiaohongshu",
        title="AI编程工具大测评",
        body="正文内容...",
        tags=["AI", "编程"],
        image_paths=[],
    )
    assert content.platform == "xiaohongshu"
    assert len(content.tags) == 2


def test_review_result_creation():
    review = ReviewResult(
        platform="xiaohongshu",
        passed=True,
        score=8.0,
        issues=[],
        suggestions=["可以增加更多数据支撑"],
    )
    assert review.passed is True
    assert review.score == 8.0


def test_pipeline_error_creation():
    error = PipelineError(agent="topic_generator", error_type="model_error", message="API timeout")
    assert error.agent == "topic_generator"


def test_pipeline_state_is_typed_dict():
    """PipelineState should be a TypedDict for LangGraph compatibility."""
    # TypedDict classes have __annotations__ but aren't regular classes
    assert hasattr(PipelineState, "__annotations__")
    assert "run_id" in PipelineState.__annotations__
    assert "user_brief" in PipelineState.__annotations__
    assert "stage" in PipelineState.__annotations__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_state.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write the implementation**

```python
# server/src/core/state.py
"""Pipeline state definitions — the data contract between all Agents."""

from __future__ import annotations

from typing import Optional, TypedDict

from pydantic import BaseModel, Field


# ── Pydantic models (validated data objects) ─────────────────────────


class UserBrief(BaseModel):
    """User input that kicks off a pipeline run."""

    topic: str = Field(description="Main topic or theme")
    keywords: list[str] = Field(default_factory=list, description="Search keywords")
    platform_hints: list[str] = Field(default_factory=list, description="Target platforms")
    style: str = Field(default="", description="Content style hint")
    extra: dict = Field(default_factory=dict, description="Arbitrary extra params")


class Topic(BaseModel):
    """A candidate topic generated by the topic agent."""

    title: str
    angle: str = Field(default="", description="The angle or hook")
    score: float = Field(default=0.0, description="Relevance/quality score 0-10")
    reasoning: str = Field(default="", description="Why this topic was chosen")


class Material(BaseModel):
    """A piece of reference material collected by the material agent."""

    source: str = Field(description="URL or file path")
    title: str = Field(default="")
    snippet: str = Field(default="", description="Relevant excerpt")
    source_type: str = Field(default="web", description="web | local_kb | manual")


class PlatformContent(BaseModel):
    """Generated content for a specific platform."""

    platform: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    image_paths: list[str] = Field(default_factory=list)
    image_prompts: list[str] = Field(default_factory=list, description="Prompts used for image gen")


class ReviewResult(BaseModel):
    """Review outcome for a piece of content."""

    platform: str
    passed: bool
    score: float = Field(default=0.0, description="Quality score 0-10")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    """Post-publish analytics and insights."""

    summary: str = Field(default="")
    insights: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class PipelineError(BaseModel):
    """An error that occurred during pipeline execution."""

    agent: str
    error_type: str
    message: str
    recoverable: bool = Field(default=True)


class StageConfig(BaseModel):
    """One stage in a pipeline YAML."""

    agent: str
    config: dict = Field(default_factory=dict)
    on_error: str = Field(default="halt", description="skip | retry | halt")
    retry_count: int = Field(default=1)


class PipelineConfig(BaseModel):
    """Loaded from YAML — describes a pipeline."""

    name: str
    description: str = ""
    platforms: list[str] = Field(default_factory=list)
    stages: list[StageConfig] = Field(default_factory=list)


# ── LangGraph State (TypedDict — not Pydantic) ──────────────────────


class PipelineState(TypedDict, total=False):
    """The shared state flowing through the LangGraph pipeline.

    Each key = one Agent's output = another Agent's input.
    Using total=False so agents only need to return the fields they produce.
    """

    # Run identity
    run_id: str
    pipeline_name: str
    user_brief: dict  # serialized UserBrief

    # Topic stage
    topics: list[dict]  # serialized list[Topic]
    selected_topic: dict  # serialized Topic

    # Material stage
    materials: list[dict]  # serialized list[Material]

    # Generation stage (keyed by platform name)
    contents: dict[str, dict]  # {platform: serialized PlatformContent}

    # Review stage
    reviews: dict[str, dict]  # {platform: serialized ReviewResult}

    # Analytics stage
    analysis: dict  # serialized Analysis

    # Flow control
    stage: str
    errors: list[dict]  # serialized list[PipelineError]
    metadata: dict
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_state.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/core/state.py server/tests/test_state.py
git commit -m "feat: add PipelineState and data models"
```

---

### Task 3: Config loader

**Files:**
- Create: `server/src/core/config.py`
- Create: `server/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_config.py
import os
import pytest
from pathlib import Path
from src.core.config import load_config, AppConfig


def test_load_config_from_yaml(tmp_path: Path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
models:
  text:
    provider: minimax
    api_key: "test-key-123"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-chat"
    max_tokens: 4096
  image:
    provider: minimax
    api_key: "test-key-456"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-image"

storage:
  db_path: "data/superpipeline.db"
  assets_dir: "data/assets"
  outputs_dir: "data/outputs"

server:
  host: "0.0.0.0"
  port: 8000
""")
    config = load_config(config_file)
    assert isinstance(config, AppConfig)
    assert config.models.text.provider == "minimax"
    assert config.models.text.api_key == "test-key-123"
    assert config.storage.db_path == "data/superpipeline.db"
    assert config.server.port == 8000


def test_load_config_env_var_substitution(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MINIMAX_API_KEY", "env-secret-key")
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
models:
  text:
    provider: minimax
    api_key: "${MINIMAX_API_KEY}"
    base_url: "https://api.minimax.chat/v1"
    model: "abab6.5-chat"
    max_tokens: 4096
storage:
  db_path: "data/test.db"
  assets_dir: "data/assets"
  outputs_dir: "data/outputs"
server:
  host: "0.0.0.0"
  port: 8000
""")
    config = load_config(config_file)
    assert config.models.text.api_key == "env-secret-key"


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_config.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write the implementation**

```python
# server/src/core/config.py
"""Configuration loader — reads YAML, substitutes env vars."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    max_tokens: int = 4096


class ModelsConfig(BaseModel):
    text: ModelConfig = Field(default_factory=lambda: ModelConfig(provider="minimax"))
    image: ModelConfig = Field(default_factory=lambda: ModelConfig(provider="minimax"))


class StorageConfig(BaseModel):
    db_path: str = "data/superpipeline.db"
    assets_dir: str = "data/assets"
    outputs_dir: str = "data/outputs"


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


_ENV_VAR_PATTERN = re.compile(r"\$\{(\w+)\}")


def _substitute_env_vars(obj: object) -> object:
    """Recursively replace ${VAR_NAME} with os.environ values."""
    if isinstance(obj, str):
        def _replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        return _ENV_VAR_PATTERN.sub(_replace, obj)
    elif isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


def load_config(path: Path) -> AppConfig:
    """Load and validate config from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text())
    resolved = _substitute_env_vars(raw)
    return AppConfig.model_validate(resolved)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_config.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/core/config.py server/tests/test_config.py
git commit -m "feat: add config loader with env var substitution"
```

---

### Task 4: Model adapter (MiniMax + OpenAI-compatible)

**Files:**
- Create: `server/src/core/models.py`
- Create: `server/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_models.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.core.models import ModelAdapter, MiniMaxAdapter, create_model_adapter
from src.core.config import ModelConfig


def test_create_model_adapter_minimax():
    config = ModelConfig(
        provider="minimax",
        api_key="test-key",
        base_url="https://api.minimax.chat/v1",
        model="abab6.5-chat",
    )
    adapter = create_model_adapter(config)
    assert isinstance(adapter, MiniMaxAdapter)


def test_create_model_adapter_unknown_provider():
    config = ModelConfig(provider="unknown_provider", api_key="test")
    with pytest.raises(ValueError, match="Unknown model provider"):
        create_model_adapter(config)


@pytest.mark.asyncio
async def test_minimax_adapter_generate():
    config = ModelConfig(
        provider="minimax",
        api_key="test-key",
        base_url="https://api.minimax.chat/v1",
        model="abab6.5-chat",
    )
    adapter = MiniMaxAdapter(config)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello world"}}]
    }

    with patch.object(adapter._client, "post", new_callable=AsyncMock, return_value=mock_response):
        result = await adapter.generate("Say hello")
        assert result == "Hello world"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_models.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write the implementation**

```python
# server/src/core/models.py
"""Model adapters — pluggable interface for text/image generation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from src.core.config import ModelConfig


class ModelAdapter(ABC):
    """Base interface for all model providers."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from a prompt."""

    @abstractmethod
    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        """Generate an image from a prompt. Returns raw bytes."""

    async def close(self) -> None:
        """Cleanup resources."""


class MiniMaxAdapter(ModelAdapter):
    """MiniMax API adapter (OpenAI-compatible chat completions endpoint)."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=60.0,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
        }
        if "size" in kwargs:
            payload["size"] = kwargs["size"]

        response = await self._client.post("/images/generations", json=payload)
        response.raise_for_status()
        data = response.json()
        # Download the image from the returned URL
        image_url = data["data"][0]["url"]
        img_response = await self._client.get(image_url)
        img_response.raise_for_status()
        return img_response.content

    async def close(self) -> None:
        await self._client.aclose()


class OpenAICompatibleAdapter(ModelAdapter):
    """Adapter for any OpenAI-compatible API (future use)."""

    def __init__(self, config: ModelConfig) -> None:
        super().__init__(config)
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=60.0,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        messages = kwargs.get("messages", [{"role": "user", "content": prompt}])
        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        response = await self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def generate_image(self, prompt: str, **kwargs) -> bytes:
        raise NotImplementedError("Image generation not supported for this provider")

    async def close(self) -> None:
        await self._client.aclose()


_ADAPTER_REGISTRY: dict[str, type[ModelAdapter]] = {
    "minimax": MiniMaxAdapter,
    "openai_compatible": OpenAICompatibleAdapter,
}


def create_model_adapter(config: ModelConfig) -> ModelAdapter:
    """Factory function — create a ModelAdapter from config."""
    adapter_cls = _ADAPTER_REGISTRY.get(config.provider)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown model provider: '{config.provider}'. "
            f"Available: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls(config)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_models.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/core/models.py server/tests/test_models.py
git commit -m "feat: add model adapters (MiniMax + OpenAI-compatible)"
```

---

### Task 5: BaseAgent and agent registry

**Files:**
- Create: `server/src/agents/base.py`
- Create: `server/src/core/registry.py`
- Create: `server/tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_registry.py
import pytest
from pydantic import BaseModel
from src.agents.base import BaseAgent
from src.core.registry import AgentRegistry, register_agent


class DummyConfig(BaseModel):
    param: str = "default"


class DummyAgent(BaseAgent):
    name = "dummy"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = DummyConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        return {"topics": [{"title": f"Topic about {inputs['user_brief']['topic']}"}]}


def test_register_and_get_agent():
    registry = AgentRegistry()
    registry.register(DummyAgent)
    agent = registry.get("dummy")
    assert isinstance(agent, DummyAgent)


def test_get_unregistered_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(KeyError, match="Agent 'nonexistent' not registered"):
        registry.get("nonexistent")


def test_register_agent_decorator():
    registry = AgentRegistry()
    decorator = register_agent(registry)

    @decorator
    class DecoratedAgent(BaseAgent):
        name = "decorated"
        consumes = ["user_brief"]
        produces = ["topics"]
        config_schema = DummyConfig

        async def run(self, inputs: dict, config: BaseModel) -> dict:
            return {"topics": []}

    agent = registry.get("decorated")
    assert isinstance(agent, DecoratedAgent)


def test_list_agents():
    registry = AgentRegistry()
    registry.register(DummyAgent)
    agents = registry.list_agents()
    assert len(agents) == 1
    assert agents[0]["name"] == "dummy"
    assert agents[0]["consumes"] == ["user_brief"]
    assert agents[0]["produces"] == ["topics"]


@pytest.mark.asyncio
async def test_agent_validate_inputs_pass():
    agent = DummyAgent()
    state = {"user_brief": {"topic": "AI"}}
    assert agent.validate_inputs(state) is True


@pytest.mark.asyncio
async def test_agent_validate_inputs_fail():
    agent = DummyAgent()
    state = {"something_else": "data"}
    assert agent.validate_inputs(state) is False


@pytest.mark.asyncio
async def test_agent_validate_outputs_pass():
    agent = DummyAgent()
    outputs = {"topics": [{"title": "Test"}]}
    assert agent.validate_outputs(outputs) is True


@pytest.mark.asyncio
async def test_agent_validate_outputs_fail():
    agent = DummyAgent()
    outputs = {"wrong_key": "data"}
    assert agent.validate_outputs(outputs) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_registry.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write BaseAgent**

```python
# server/src/agents/base.py
"""Base class for all pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import jinja2
from pydantic import BaseModel

from src.core.models import ModelAdapter


class BaseAgent(ABC):
    """Standard interface every Agent must implement.

    Attributes:
        name: Unique identifier, used in YAML pipeline configs.
        consumes: State keys this agent reads.
        produces: State keys this agent writes.
        config_schema: Pydantic model for runtime config from YAML.
    """

    name: ClassVar[str]
    consumes: ClassVar[list[str]]
    produces: ClassVar[list[str]]
    config_schema: ClassVar[type[BaseModel]]

    def __init__(self, model: ModelAdapter | None = None) -> None:
        self.model = model
        self._jinja_env: jinja2.Environment | None = None

    @abstractmethod
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        """Execute this agent's logic.

        Args:
            inputs: Dict of state values for keys in `consumes`.
            config: Validated config from pipeline YAML.

        Returns:
            Dict of state updates for keys in `produces`.
        """

    def validate_inputs(self, state: dict) -> bool:
        """Check that all consumed keys exist and are not None in state."""
        return all(
            key in state and state[key] is not None
            for key in self.consumes
        )

    def validate_outputs(self, outputs: dict) -> bool:
        """Check that all produced keys are present in outputs."""
        return all(key in outputs for key in self.produces)

    def load_prompt(self, template_name: str, **kwargs) -> str:
        """Load and render a Jinja2 template from this agent's prompts/ dir."""
        if self._jinja_env is None:
            prompts_dir = Path(__file__).parent / self.name / "prompts"
            self._jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(prompts_dir)),
                undefined=jinja2.StrictUndefined,
            )
        template = self._jinja_env.get_template(template_name)
        return template.render(**kwargs)
```

- [ ] **Step 4: Write AgentRegistry**

```python
# server/src/core/registry.py
"""Agent registry — discovers and manages agent instances."""

from __future__ import annotations

from typing import Callable

from src.agents.base import BaseAgent
from src.core.models import ModelAdapter


class AgentRegistry:
    """Registry of all available agents."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent_cls: type[BaseAgent], model: ModelAdapter | None = None) -> None:
        """Register an agent class, instantiating it."""
        instance = agent_cls(model=model)
        self._agents[agent_cls.name] = instance

    def get(self, name: str) -> BaseAgent:
        """Get a registered agent by name."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not registered. Available: {list(self._agents.keys())}")
        return self._agents[name]

    def list_agents(self) -> list[dict]:
        """List all registered agents with their metadata."""
        return [
            {
                "name": agent.name,
                "consumes": agent.consumes,
                "produces": agent.produces,
                "config_schema": agent.config_schema.__name__,
            }
            for agent in self._agents.values()
        ]

    def has(self, name: str) -> bool:
        """Check if an agent is registered."""
        return name in self._agents


def register_agent(registry: AgentRegistry) -> Callable:
    """Decorator factory for registering agents."""
    def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
        registry.register(cls)
        return cls
    return decorator
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_registry.py -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/src/agents/base.py server/src/core/registry.py server/tests/test_registry.py
git commit -m "feat: add BaseAgent and AgentRegistry"
```

---

### Task 6: Pipeline config loader

**Files:**
- Create: `server/src/core/pipeline_loader.py`
- Create: `server/tests/test_pipeline_loader.py`
- Create: `server/pipelines/xiaohongshu_image_text.yaml`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_pipeline_loader.py
import pytest
from pathlib import Path
from src.core.pipeline_loader import load_pipeline, list_pipelines
from src.core.state import PipelineConfig


def test_load_pipeline_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "test_pipeline.yaml"
    yaml_file.write_text("""
name: "Test Pipeline"
description: "A test pipeline"
platforms: ["xiaohongshu"]
stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
""")
    config = load_pipeline(yaml_file)
    assert isinstance(config, PipelineConfig)
    assert config.name == "Test Pipeline"
    assert len(config.stages) == 2
    assert config.stages[0].agent == "topic_generator"
    assert config.stages[0].config["style"] == "种草"


def test_load_pipeline_not_found():
    with pytest.raises(FileNotFoundError):
        load_pipeline(Path("/nonexistent.yaml"))


def test_list_pipelines(tmp_path: Path):
    (tmp_path / "pipeline_a.yaml").write_text("name: A\nstages: []")
    (tmp_path / "pipeline_b.yaml").write_text("name: B\nstages: []")
    (tmp_path / "not_yaml.txt").write_text("ignore me")

    pipelines = list_pipelines(tmp_path)
    assert len(pipelines) == 2
    names = {p["name"] for p in pipelines}
    assert names == {"A", "B"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_pipeline_loader.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write the implementation**

```python
# server/src/core/pipeline_loader.py
"""Pipeline YAML config loader."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.core.state import PipelineConfig


def load_pipeline(path: Path) -> PipelineConfig:
    """Load a pipeline config from a YAML file."""
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {path}")
    raw = yaml.safe_load(path.read_text())
    return PipelineConfig.model_validate(raw)


def list_pipelines(directory: Path) -> list[dict]:
    """List all pipeline configs in a directory."""
    pipelines = []
    for yaml_file in sorted(directory.glob("*.yaml")):
        try:
            config = load_pipeline(yaml_file)
            pipelines.append({
                "name": config.name,
                "description": config.description,
                "platforms": config.platforms,
                "stages": len(config.stages),
                "file": yaml_file.name,
            })
        except Exception:
            continue  # skip malformed files
    return pipelines
```

- [ ] **Step 4: Create the first real pipeline YAML**

```yaml
# server/pipelines/xiaohongshu_image_text.yaml
name: "小红书图文"
description: "生成小红书种草图文内容"
platforms: ["xiaohongshu"]

stages:
  - agent: topic_generator
    config:
      style: "种草"
      count: 5

  - agent: material_collector
    config:
      sources: ["web"]
      max_items: 10

  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text

  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0

  - agent: analyst
    config:
      metrics: ["engagement", "reach"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_pipeline_loader.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/src/core/pipeline_loader.py server/tests/test_pipeline_loader.py server/pipelines/xiaohongshu_image_text.yaml
git commit -m "feat: add pipeline YAML loader and first pipeline config"
```

---

### Task 7: Orchestrator (LangGraph dynamic graph builder)

**Files:**
- Create: `server/src/core/orchestrator.py`
- Create: `server/tests/test_orchestrator.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_orchestrator.py
import pytest
from pydantic import BaseModel
from src.core.orchestrator import Orchestrator
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, StageConfig, UserBrief
from src.agents.base import BaseAgent


class EchoConfig(BaseModel):
    prefix: str = "echo"


class EchoTopicAgent(BaseAgent):
    name = "echo_topic"
    consumes = ["user_brief"]
    produces = ["topics"]
    config_schema = EchoConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        brief = UserBrief.model_validate(inputs["user_brief"])
        return {"topics": [{"title": f"{config.prefix}: {brief.topic}", "angle": "", "score": 9.0}]}


class EchoContentAgent(BaseAgent):
    name = "echo_content"
    consumes = ["topics"]
    produces = ["contents"]
    config_schema = EchoConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        title = inputs["topics"][0]["title"]
        return {
            "contents": {
                "test_platform": {
                    "platform": "test_platform",
                    "title": title,
                    "body": f"Content about: {title}",
                    "tags": [],
                    "image_paths": [],
                }
            }
        }


@pytest.fixture
def registry():
    reg = AgentRegistry()
    reg.register(EchoTopicAgent)
    reg.register(EchoContentAgent)
    return reg


@pytest.fixture
def pipeline_config():
    return PipelineConfig(
        name="test",
        description="test pipeline",
        platforms=["test_platform"],
        stages=[
            StageConfig(agent="echo_topic", config={"prefix": "TEST"}),
            StageConfig(agent="echo_content", config={"prefix": "GEN"}),
        ],
    )


@pytest.mark.asyncio
async def test_orchestrator_builds_and_runs(registry, pipeline_config):
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=pipeline_config,
        user_brief=UserBrief(topic="AI tools", keywords=["AI"]),
    )
    assert result["stage"] == "completed"
    assert len(result["topics"]) == 1
    assert result["topics"][0]["title"] == "TEST: AI tools"
    assert "test_platform" in result["contents"]
    assert result["contents"]["test_platform"]["body"] == "Content about: TEST: AI tools"


@pytest.mark.asyncio
async def test_orchestrator_returns_run_id(registry, pipeline_config):
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=pipeline_config,
        user_brief=UserBrief(topic="test"),
    )
    assert "run_id" in result
    assert len(result["run_id"]) > 0


@pytest.mark.asyncio
async def test_orchestrator_handles_agent_error(registry):
    """If an agent raises, error is captured in state.errors."""

    class FailingAgent(BaseAgent):
        name = "failing_agent"
        consumes = ["user_brief"]
        produces = ["topics"]
        config_schema = EchoConfig

        async def run(self, inputs, config):
            raise RuntimeError("Intentional failure")

    registry.register(FailingAgent)

    config = PipelineConfig(
        name="fail_test",
        stages=[StageConfig(agent="failing_agent", config={})],
    )
    orch = Orchestrator(registry)
    result = await orch.run(
        pipeline_config=config,
        user_brief=UserBrief(topic="test"),
    )
    assert result["stage"] == "failed"
    assert len(result["errors"]) > 0
    assert result["errors"][0]["agent"] == "failing_agent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write the implementation**

```python
# server/src/core/orchestrator.py
"""Orchestrator — dynamically builds LangGraph pipelines from YAML config."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.base import BaseAgent
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, PipelineState, StageConfig, UserBrief


class Orchestrator:
    """Reads pipeline config, assembles a LangGraph StateGraph, and runs it."""

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self.checkpointer = MemorySaver()

    def _wrap_agent(self, agent: BaseAgent, stage_config: StageConfig):
        """Wrap an agent into a LangGraph node function with retry and on_error support."""
        config = agent.config_schema.model_validate(stage_config.config)
        on_error = stage_config.on_error  # "skip" | "retry" | "halt"
        retry_count = stage_config.retry_count

        async def node_fn(state: PipelineState) -> dict:
            # Update stage
            updates: dict[str, Any] = {"stage": agent.name}

            # Validate inputs
            if not agent.validate_inputs(state):
                error = {
                    "agent": agent.name,
                    "error_type": "validation_error",
                    "message": f"Missing required inputs: {agent.consumes}",
                    "recoverable": False,
                }
                errors = list(state.get("errors", []))
                errors.append(error)
                updates["errors"] = errors
                if on_error == "skip":
                    return updates  # stage stays current name, not "failed"
                updates["stage"] = "failed"
                return updates

            # Extract inputs
            inputs = {key: state[key] for key in agent.consumes if key in state}

            # Retry loop
            last_exception = None
            for attempt in range(max(1, retry_count)):
                try:
                    outputs = await agent.run(inputs, config)
                    # Validate outputs
                    if not agent.validate_outputs(outputs):
                        raise ValueError(f"Agent did not produce required outputs: {agent.produces}")
                    # Merge dict fields (e.g. contents, reviews) instead of replacing
                    for key, value in outputs.items():
                        if isinstance(value, dict) and isinstance(state.get(key), dict):
                            merged = dict(state[key])
                            merged.update(value)
                            updates[key] = merged
                        else:
                            updates[key] = value
                    return updates
                except Exception as e:
                    last_exception = e
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # linear backoff

            # All retries exhausted
            error = {
                "agent": agent.name,
                "error_type": type(last_exception).__name__,
                "message": str(last_exception),
                "recoverable": on_error != "halt",
            }
            errors = list(state.get("errors", []))
            errors.append(error)
            updates["errors"] = errors

            if on_error == "skip":
                return updates  # continue to next stage
            elif on_error == "halt":
                updates["stage"] = "failed"
            # on_error == "retry" already exhausted retries, treat as halt
            else:
                updates["stage"] = "failed"

            return updates

        return node_fn

    def build_graph(self, pipeline_config: PipelineConfig) -> StateGraph:
        """Build a LangGraph StateGraph from pipeline config."""
        graph = StateGraph(PipelineState)

        stages = pipeline_config.stages
        if not stages:
            raise ValueError("Pipeline has no stages")

        # Add nodes
        for stage in stages:
            agent = self.registry.get(stage.agent)
            graph.add_node(stage.agent, self._wrap_agent(agent, stage))

        # Wire edges: START -> stage[0] -> stage[1] -> ... -> END
        graph.add_edge(START, stages[0].agent)
        for i in range(len(stages) - 1):
            # Conditional: if stage failed, go to END; else continue
            current = stages[i].agent
            next_stage = stages[i + 1].agent
            graph.add_conditional_edges(
                current,
                lambda state, _next=next_stage: _next if state.get("stage") != "failed" else END,
            )
        graph.add_edge(stages[-1].agent, END)

        return graph

    async def run(
        self,
        pipeline_config: PipelineConfig,
        user_brief: UserBrief,
        run_id: str | None = None,
    ) -> dict:
        """Build and execute a pipeline."""
        run_id = run_id or uuid.uuid4().hex[:12]
        graph = self.build_graph(pipeline_config)
        compiled = graph.compile(checkpointer=self.checkpointer)

        initial_state: dict[str, Any] = {
            "run_id": run_id,
            "pipeline_name": pipeline_config.name,
            "user_brief": user_brief.model_dump(),
            "topics": [],
            "materials": [],
            "contents": {},
            "reviews": {},
            "analysis": {},
            "stage": "starting",
            "errors": [],
            "metadata": {},
        }

        config = {"configurable": {"thread_id": run_id}}
        result = await compiled.ainvoke(initial_state, config=config)

        # Mark completed if not failed
        if result.get("stage") != "failed":
            result["stage"] = "completed"

        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_orchestrator.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/src/core/orchestrator.py server/tests/test_orchestrator.py
git commit -m "feat: add Orchestrator with dynamic LangGraph graph building"
```

---

### Task 8: Storage layer (SQLite + file store)

**Files:**
- Create: `server/src/storage/models.py`
- Create: `server/src/storage/state_store.py`
- Create: `server/src/storage/asset_store.py`
- Create: `server/tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_storage.py
import pytest
from pathlib import Path
from src.storage.state_store import StateStore
from src.storage.asset_store import AssetStore


@pytest.fixture
async def state_store(tmp_path):
    store = StateStore(str(tmp_path / "test.db"))
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def asset_store(tmp_path):
    return AssetStore(
        assets_dir=str(tmp_path / "assets"),
        outputs_dir=str(tmp_path / "outputs"),
    )


@pytest.mark.asyncio
async def test_save_and_get_run(state_store):
    await state_store.save_run(
        run_id="test-run-1",
        pipeline_name="test_pipeline",
        status="running",
        state={"stage": "topic_generator"},
    )
    run = await state_store.get_run("test-run-1")
    assert run is not None
    assert run["pipeline_name"] == "test_pipeline"
    assert run["status"] == "running"


@pytest.mark.asyncio
async def test_update_run_status(state_store):
    await state_store.save_run("run-2", "test", "running", {})
    await state_store.update_run("run-2", status="completed", state={"stage": "completed"})
    run = await state_store.get_run("run-2")
    assert run["status"] == "completed"


@pytest.mark.asyncio
async def test_list_runs(state_store):
    await state_store.save_run("run-a", "pipeline_a", "completed", {})
    await state_store.save_run("run-b", "pipeline_b", "running", {})
    runs = await state_store.list_runs(limit=10)
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_save_and_get_content(state_store):
    await state_store.save_content(
        content_id="content-1",
        run_id="run-1",
        platform="xiaohongshu",
        title="Test Title",
        body="Test body",
        status="pending_review",
    )
    content = await state_store.get_content("content-1")
    assert content is not None
    assert content["platform"] == "xiaohongshu"
    assert content["title"] == "Test Title"


@pytest.mark.asyncio
async def test_list_contents_by_status(state_store):
    await state_store.save_content("c1", "r1", "xiaohongshu", "T1", "B1", "approved")
    await state_store.save_content("c2", "r1", "x", "T2", "B2", "pending_review")
    approved = await state_store.list_contents(status="approved")
    assert len(approved) == 1
    assert approved[0]["content_id"] == "c1"


def test_asset_store_creates_dirs(asset_store):
    run_dir = asset_store.get_output_dir("test-run")
    assert run_dir.exists()


def test_asset_store_save_and_read(asset_store):
    output_dir = asset_store.get_output_dir("run-1")
    file_path = asset_store.save_file(output_dir, "test.txt", b"hello world")
    assert file_path.exists()
    assert file_path.read_bytes() == b"hello world"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_storage.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write state_store.py**

```python
# server/src/storage/state_store.py
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
        """Create tables if they don't exist."""
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

    # ── Pipeline runs ────────────────────────────────────────

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

    # ── Contents ─────────────────────────────────────────────

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
```

- [ ] **Step 4: Write asset_store.py**

```python
# server/src/storage/asset_store.py
"""File-based storage for content assets (images, generated files)."""

from __future__ import annotations

from pathlib import Path


class AssetStore:
    """Manages file storage for pipeline assets."""

    def __init__(self, assets_dir: str, outputs_dir: str) -> None:
        self.assets_dir = Path(assets_dir)
        self.outputs_dir = Path(outputs_dir)

    def get_asset_dir(self, run_id: str) -> Path:
        """Get or create the assets directory for a run."""
        d = self.assets_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_output_dir(self, run_id: str) -> Path:
        """Get or create the outputs directory for a run."""
        d = self.outputs_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_file(self, directory: Path, filename: str, data: bytes) -> Path:
        """Save bytes to a file, return the path."""
        file_path = directory / filename
        file_path.write_bytes(data)
        return file_path

    def read_file(self, file_path: Path) -> bytes:
        """Read a file and return bytes."""
        return file_path.read_bytes()

    def list_files(self, directory: Path) -> list[Path]:
        """List all files in a directory."""
        if not directory.exists():
            return []
        return sorted(f for f in directory.iterdir() if f.is_file())
```

- [ ] **Step 5: Write storage/models.py (empty placeholder for DB models)**

```python
# server/src/storage/models.py
"""Database model constants and helpers."""

# Content status values
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_PUBLISHED = "published"

# Run status values
RUN_STATUS_PENDING = "pending"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"

ALL_CONTENT_STATUSES = [STATUS_PENDING_REVIEW, STATUS_APPROVED, STATUS_REJECTED, STATUS_PUBLISHED]
ALL_RUN_STATUSES = [RUN_STATUS_PENDING, RUN_STATUS_RUNNING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_storage.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add server/src/storage/ server/tests/test_storage.py
git commit -m "feat: add SQLite state store and file asset store"
```

---

## Phase 2: Platform Adapters + Agents

### Task 9: Platform adapter base + Xiaohongshu + X

**Files:**
- Create: `server/src/platforms/base.py`
- Create: `server/src/platforms/xiaohongshu.py`
- Create: `server/src/platforms/x_twitter.py`
- Create: `server/tests/test_platforms.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_platforms.py
import pytest
from src.platforms.base import BasePlatform, get_platform
from src.platforms.xiaohongshu import XiaohongshuPlatform
from src.platforms.x_twitter import XPlatform


def test_xiaohongshu_max_text_length():
    p = XiaohongshuPlatform()
    assert p.name == "xiaohongshu"
    assert p.max_text_length == 1000


def test_xiaohongshu_validate_pass():
    p = XiaohongshuPlatform()
    issues = p.validate({"body": "一篇正常的小红书笔记内容", "tags": ["#测试"]})
    assert len(issues) == 0


def test_xiaohongshu_validate_too_long():
    p = XiaohongshuPlatform()
    issues = p.validate({"body": "x" * 1001, "tags": []})
    assert any("字数" in i or "length" in i.lower() for i in issues)


def test_xiaohongshu_format_adds_tags():
    p = XiaohongshuPlatform()
    result = p.format_content("正文内容", tags=["AI", "工具"])
    assert "#AI" in result
    assert "#工具" in result


def test_x_platform_max_length():
    p = XPlatform()
    assert p.name == "x"
    assert p.max_text_length == 280


def test_x_validate_too_long():
    p = XPlatform()
    issues = p.validate({"body": "x" * 281, "tags": []})
    assert len(issues) > 0


def test_get_platform_by_name():
    p = get_platform("xiaohongshu")
    assert isinstance(p, XiaohongshuPlatform)

    p2 = get_platform("x")
    assert isinstance(p2, XPlatform)


def test_get_platform_unknown():
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform("tiktok")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_platforms.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write base.py**

```python
# server/src/platforms/base.py
"""Base platform adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BasePlatform(ABC):
    """Interface for platform-specific content rules."""

    name: str
    max_text_length: int
    max_tags: int = 30
    max_images: int = 9

    @abstractmethod
    def validate(self, content: dict) -> list[str]:
        """Validate content against platform rules. Returns list of issues."""

    @abstractmethod
    def format_content(self, body: str, **kwargs) -> str:
        """Format raw content to platform conventions."""

    def get_rules_prompt(self) -> str:
        """Return platform rules as a prompt snippet for content generation."""
        return f"Platform: {self.name}, max {self.max_text_length} chars, max {self.max_tags} tags, max {self.max_images} images."


_PLATFORM_REGISTRY: dict[str, type[BasePlatform]] = {}


def register_platform(cls: type[BasePlatform]) -> type[BasePlatform]:
    """Decorator to register a platform adapter."""
    _PLATFORM_REGISTRY[cls.name] = cls
    return cls


def get_platform(name: str) -> BasePlatform:
    """Get a platform adapter instance by name."""
    cls = _PLATFORM_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown platform: '{name}'. Available: {list(_PLATFORM_REGISTRY.keys())}")
    return cls()


def list_platforms() -> list[str]:
    """List all registered platform names."""
    return list(_PLATFORM_REGISTRY.keys())
```

- [ ] **Step 4: Write xiaohongshu.py**

```python
# server/src/platforms/xiaohongshu.py
"""Xiaohongshu (小红书) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class XiaohongshuPlatform(BasePlatform):
    name = "xiaohongshu"
    max_text_length = 1000
    max_tags = 30
    max_images = 9

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])

        if len(body) > self.max_text_length:
            issues.append(f"正文字数 {len(body)} 超过限制 {self.max_text_length}")
        if len(body) < 20:
            issues.append("正文内容过短，建议至少 20 字")
        if len(tags) > self.max_tags:
            issues.append(f"标签数 {len(tags)} 超过限制 {self.max_tags}")
        return issues

    def format_content(self, body: str, **kwargs) -> str:
        tags = kwargs.get("tags", [])
        formatted = body.strip()
        if tags:
            tag_line = " ".join(f"#{t}" for t in tags)
            formatted = f"{formatted}\n\n{tag_line}"
        return formatted

    def get_rules_prompt(self) -> str:
        return (
            "平台：小红书。要求：\n"
            f"- 正文不超过 {self.max_text_length} 字\n"
            "- 标题要有吸引力，可用 emoji\n"
            "- 正文分段清晰，善用列表\n"
            "- 结尾加话题标签\n"
            f"- 最多 {self.max_images} 张配图\n"
            "- 风格：真实分享、种草、干货向"
        )
```

- [ ] **Step 5: Write x_twitter.py**

```python
# server/src/platforms/x_twitter.py
"""X (Twitter) platform adapter."""

from src.platforms.base import BasePlatform, register_platform


@register_platform
class XPlatform(BasePlatform):
    name = "x"
    max_text_length = 280
    max_tags = 5
    max_images = 4

    def validate(self, content: dict) -> list[str]:
        issues = []
        body = content.get("body", "")
        tags = content.get("tags", [])

        if len(body) > self.max_text_length:
            issues.append(f"Tweet length {len(body)} exceeds {self.max_text_length} limit")
        if len(tags) > self.max_tags:
            issues.append(f"Too many hashtags: {len(tags)}, max {self.max_tags}")
        return issues

    def format_content(self, body: str, **kwargs) -> str:
        tags = kwargs.get("tags", [])
        formatted = body.strip()
        if tags:
            tag_line = " ".join(f"#{t}" for t in tags[:self.max_tags])
            # Only add tags if total length fits
            if len(formatted) + len(tag_line) + 2 <= self.max_text_length:
                formatted = f"{formatted}\n\n{tag_line}"
        return formatted

    def get_rules_prompt(self) -> str:
        return (
            "Platform: X (Twitter). Requirements:\n"
            f"- Max {self.max_text_length} characters per tweet\n"
            "- Be concise and punchy\n"
            f"- Max {self.max_tags} hashtags\n"
            f"- Max {self.max_images} images\n"
            "- Engage with questions or hot takes"
        )
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_platforms.py -v`
Expected: All 8 tests PASS

- [ ] **Step 7: Commit**

```bash
git add server/src/platforms/ server/tests/test_platforms.py
git commit -m "feat: add platform adapters for Xiaohongshu and X"
```

---

### Task 10: Topic Generator Agent

**Files:**
- Create: `server/src/agents/topic_generator/__init__.py`
- Create: `server/src/agents/topic_generator/agent.py`
- Create: `server/src/agents/topic_generator/schemas.py`
- Create: `server/src/agents/topic_generator/prompts/generate.j2`
- Create: `server/src/agents/topic_generator/README.md`
- Create: `server/tests/agents/test_topic_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/agents/test_topic_generator.py
import pytest
import json
from unittest.mock import AsyncMock
from src.agents.topic_generator.agent import TopicGeneratorAgent
from src.agents.topic_generator.schemas import TopicGenConfig
from src.core.state import UserBrief


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps([
        {"title": "AI编程工具横评", "angle": "测评对比", "score": 8.5, "reasoning": "热门话题"},
        {"title": "程序员效率提升指南", "angle": "实用技巧", "score": 7.0, "reasoning": "常青选题"},
    ]))
    return model


def test_topic_generator_metadata():
    assert TopicGeneratorAgent.name == "topic_generator"
    assert TopicGeneratorAgent.consumes == ["user_brief"]
    assert TopicGeneratorAgent.produces == ["topics", "selected_topic"]


@pytest.mark.asyncio
async def test_topic_generator_run(mock_model):
    agent = TopicGeneratorAgent(model=mock_model)
    config = TopicGenConfig(style="种草", count=5)
    inputs = {"user_brief": UserBrief(topic="AI tools", keywords=["AI", "coding"]).model_dump()}

    result = await agent.run(inputs, config)

    assert "topics" in result
    assert "selected_topic" in result
    assert len(result["topics"]) == 2
    assert result["selected_topic"]["title"] == "AI编程工具横评"  # highest score
    mock_model.generate.assert_called_once()


@pytest.mark.asyncio
async def test_topic_generator_handles_bad_json(mock_model):
    mock_model.generate = AsyncMock(return_value="not valid json")
    agent = TopicGeneratorAgent(model=mock_model)
    config = TopicGenConfig()
    inputs = {"user_brief": UserBrief(topic="test").model_dump()}

    with pytest.raises(ValueError, match="parse"):
        await agent.run(inputs, config)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/agents/test_topic_generator.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write schemas.py**

```python
# server/src/agents/topic_generator/schemas.py
"""Topic generator agent configuration and schemas."""

from pydantic import BaseModel, Field


class TopicGenConfig(BaseModel):
    """Runtime config for topic generation (from pipeline YAML)."""

    style: str = Field(default="", description="Content style hint (e.g. 种草, 测评, 干货)")
    count: int = Field(default=5, description="Number of candidate topics to generate")
    temperature: float = Field(default=0.8, description="LLM temperature for creativity")
```

- [ ] **Step 4: Write the prompt template**

```jinja2
{# server/src/agents/topic_generator/prompts/generate.j2 #}
你是一个专业的内容选题策划专家。请根据以下信息生成 {{ count }} 个候选选题。

## 输入信息
- 主题方向：{{ topic }}
{% if keywords %}- 关键词：{{ keywords | join(', ') }}{% endif %}
{% if style %}- 内容风格：{{ style }}{% endif %}
{% if platform_hints %}- 目标平台：{{ platform_hints | join(', ') }}{% endif %}

## 要求
1. 每个选题需要有明确的角度和切入点
2. 选题要有吸引力，能引发目标读者的兴趣
3. 评分标准：话题热度、差异化、可执行性（0-10分）

## 输出格式
请以 JSON 数组格式输出，每个元素包含：
```json
[
  {
    "title": "选题标题",
    "angle": "切入角度",
    "score": 8.5,
    "reasoning": "选择理由"
  }
]
```

只输出 JSON 数组，不要其他内容。
```

- [ ] **Step 5: Write agent.py**

```python
# server/src/agents/topic_generator/agent.py
"""Topic Generator Agent — generates candidate topics from a user brief."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.topic_generator.schemas import TopicGenConfig
from src.core.state import Topic, UserBrief


class TopicGeneratorAgent(BaseAgent):
    name = "topic_generator"
    consumes = ["user_brief"]
    produces = ["topics", "selected_topic"]
    config_schema = TopicGenConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: TopicGenConfig = config
        brief = UserBrief.model_validate(inputs["user_brief"])

        prompt = self.load_prompt(
            "generate.j2",
            topic=brief.topic,
            keywords=brief.keywords,
            style=cfg.style or brief.style,
            platform_hints=brief.platform_hints,
            count=cfg.count,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        # Parse response as JSON array of topics
        try:
            raw_topics = json.loads(response.strip())
            if not isinstance(raw_topics, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse topic generation response: {e}") from e

        topics = [Topic.model_validate(t).model_dump() for t in raw_topics]

        # Auto-select the highest scored topic
        selected = max(topics, key=lambda t: t.get("score", 0)) if topics else None

        return {"topics": topics, "selected_topic": selected}
```

- [ ] **Step 6: Write __init__.py**

```python
# server/src/agents/topic_generator/__init__.py
"""Topic Generator Agent module."""

from src.agents.topic_generator.agent import TopicGeneratorAgent

__all__ = ["TopicGeneratorAgent"]
```

- [ ] **Step 7: Write README.md**

```markdown
# Topic Generator Agent

## Purpose
Generates candidate content topics from a user brief using an LLM.

## Consumes
- `user_brief`: UserBrief — topic, keywords, platform hints, style

## Produces
- `topics`: list[Topic] — candidate topics with scores
- `selected_topic`: Topic — highest-scored topic (auto-selected)

## Config (from pipeline YAML)
| Key | Type | Default | Description |
|-----|------|---------|-------------|
| style | str | "" | Content style hint |
| count | int | 5 | Number of topics to generate |
| temperature | float | 0.8 | LLM creativity |

## How it works
1. Loads the `generate.j2` prompt template
2. Fills in brief details + config
3. Calls the text model
4. Parses JSON response into Topic objects
5. Auto-selects the highest scored topic
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd server && python -m pytest tests/agents/test_topic_generator.py -v`
Expected: All 3 tests PASS

- [ ] **Step 9: Commit**

```bash
git add server/src/agents/topic_generator/ server/tests/agents/test_topic_generator.py
git commit -m "feat: add Topic Generator Agent"
```

---

### Task 11: Material Collector Agent

**Files:**
- Create: `server/src/agents/material_collector/__init__.py`
- Create: `server/src/agents/material_collector/agent.py`
- Create: `server/src/agents/material_collector/schemas.py`
- Create: `server/src/agents/material_collector/prompts/collect.j2`
- Create: `server/tests/agents/test_material_collector.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/agents/test_material_collector.py
import pytest
import json
from unittest.mock import AsyncMock
from src.agents.material_collector.agent import MaterialCollectorAgent
from src.agents.material_collector.schemas import MaterialCollectConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps([
        {"source": "https://example.com/article1", "title": "AI Tools Overview", "snippet": "A comprehensive review...", "source_type": "web"},
        {"source": "https://example.com/article2", "title": "Coding with AI", "snippet": "How AI changes...", "source_type": "web"},
    ]))
    return model


def test_material_collector_metadata():
    assert MaterialCollectorAgent.name == "material_collector"
    assert MaterialCollectorAgent.consumes == ["selected_topic"]
    assert MaterialCollectorAgent.produces == ["materials"]


@pytest.mark.asyncio
async def test_material_collector_run(mock_model):
    agent = MaterialCollectorAgent(model=mock_model)
    config = MaterialCollectConfig(sources=["web"], max_items=10)
    inputs = {"selected_topic": {"title": "AI Tools Review", "angle": "comparison", "score": 8.5}}

    result = await agent.run(inputs, config)

    assert "materials" in result
    assert len(result["materials"]) == 2
    assert result["materials"][0]["source_type"] == "web"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/agents/test_material_collector.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write schemas.py**

```python
# server/src/agents/material_collector/schemas.py
from pydantic import BaseModel, Field


class MaterialCollectConfig(BaseModel):
    sources: list[str] = Field(default=["web"], description="Data sources: web, local_kb")
    max_items: int = Field(default=10, description="Max materials to collect")
    temperature: float = Field(default=0.3, description="Lower temp for factual retrieval")
```

- [ ] **Step 4: Write the prompt template**

```jinja2
{# server/src/agents/material_collector/prompts/collect.j2 #}
你是一个专业的内容研究员。请根据以下选题，收集相关的参考素材。

## 选题信息
- 标题：{{ title }}
- 角度：{{ angle }}

## 要求
1. 模拟搜索并生成 {{ max_items }} 条相关参考素材
2. 每条素材需要包含来源、标题和关键摘要
3. 素材要多样化：不同角度、不同来源

## 输出格式
JSON 数组，每个元素：
```json
[
  {
    "source": "来源URL或路径",
    "title": "素材标题",
    "snippet": "关键摘要内容（100字以内）",
    "source_type": "web"
  }
]
```

只输出 JSON 数组，不要其他内容。
```

- [ ] **Step 5: Write agent.py**

```python
# server/src/agents/material_collector/agent.py
"""Material Collector Agent — gathers reference materials for a topic."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.material_collector.schemas import MaterialCollectConfig
from src.core.state import Material, Topic


class MaterialCollectorAgent(BaseAgent):
    name = "material_collector"
    consumes = ["selected_topic"]
    produces = ["materials"]
    config_schema = MaterialCollectConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: MaterialCollectConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])

        prompt = self.load_prompt(
            "collect.j2",
            title=topic.title,
            angle=topic.angle,
            max_items=cfg.max_items,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_materials = json.loads(response.strip())
            if not isinstance(raw_materials, list):
                raise ValueError("Expected a JSON array")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse materials response: {e}") from e

        materials = [Material.model_validate(m).model_dump() for m in raw_materials]
        return {"materials": materials}
```

- [ ] **Step 6: Write __init__.py**

```python
# server/src/agents/material_collector/__init__.py
from src.agents.material_collector.agent import MaterialCollectorAgent
__all__ = ["MaterialCollectorAgent"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd server && python -m pytest tests/agents/test_material_collector.py -v`
Expected: All 2 tests PASS

- [ ] **Step 8: Commit**

```bash
git add server/src/agents/material_collector/ server/tests/agents/test_material_collector.py
git commit -m "feat: add Material Collector Agent"
```

---

### Task 12: Content Generator Agent

**Files:**
- Create: `server/src/agents/content_generator/__init__.py`
- Create: `server/src/agents/content_generator/agent.py`
- Create: `server/src/agents/content_generator/schemas.py`
- Create: `server/src/agents/content_generator/prompts/generate.j2`
- Create: `server/tests/agents/test_content_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/agents/test_content_generator.py
import pytest
import json
from unittest.mock import AsyncMock
from src.agents.content_generator.agent import ContentGeneratorAgent
from src.agents.content_generator.schemas import ContentGenConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "title": "AI编程工具大测评 🔥",
        "body": "最近用了好几款AI编程工具...\n\n1. Cursor\n2. Copilot\n3. Claude Code",
        "tags": ["AI", "编程", "工具测评"],
        "image_prompts": ["A comparison chart of AI coding tools"],
    }))
    return model


def test_content_generator_metadata():
    assert ContentGeneratorAgent.name == "content_generator"
    assert "selected_topic" in ContentGeneratorAgent.consumes
    assert "materials" in ContentGeneratorAgent.consumes
    assert ContentGeneratorAgent.produces == ["contents"]


@pytest.mark.asyncio
async def test_content_generator_run(mock_model):
    agent = ContentGeneratorAgent(model=mock_model)
    config = ContentGenConfig(platform="xiaohongshu", format="image_text")
    inputs = {
        "selected_topic": {"title": "AI Tools Review", "angle": "comparison", "score": 8.5},
        "materials": [{"source": "https://example.com", "title": "Ref", "snippet": "data", "source_type": "web"}],
    }

    result = await agent.run(inputs, config)

    assert "contents" in result
    assert "xiaohongshu" in result["contents"]
    content = result["contents"]["xiaohongshu"]
    assert content["platform"] == "xiaohongshu"
    assert len(content["title"]) > 0
    assert len(content["body"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/agents/test_content_generator.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write schemas.py**

```python
# server/src/agents/content_generator/schemas.py
from pydantic import BaseModel, Field


class ContentGenConfig(BaseModel):
    platform: str = Field(description="Target platform name")
    format: str = Field(default="image_text", description="Content format: image_text, text_only, thread")
    temperature: float = Field(default=0.7)
    style: str = Field(default="", description="Override style")
```

- [ ] **Step 4: Write the prompt template**

```jinja2
{# server/src/agents/content_generator/prompts/generate.j2 #}
你是一个专业的内容创作者。请根据选题和素材，生成适合「{{ platform }}」平台的{{ format }}内容。

## 选题
- 标题：{{ topic_title }}
- 角度：{{ topic_angle }}

## 参考素材
{% for m in materials %}
- 《{{ m.title }}》：{{ m.snippet }}
{% endfor %}

## 平台规则
{{ platform_rules }}

{% if style %}## 风格要求：{{ style }}{% endif %}

## 输出格式
JSON 对象：
```json
{
  "title": "内容标题",
  "body": "完整正文",
  "tags": ["标签1", "标签2"],
  "image_prompts": ["图片生成提示词1"]
}
```

只输出 JSON 对象，不要其他内容。
```

- [ ] **Step 5: Write agent.py**

```python
# server/src/agents/content_generator/agent.py
"""Content Generator Agent — creates platform-specific content."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.content_generator.schemas import ContentGenConfig
from src.core.state import PlatformContent, Topic, Material
from src.platforms.base import get_platform


class ContentGeneratorAgent(BaseAgent):
    name = "content_generator"
    consumes = ["selected_topic", "materials"]
    produces = ["contents"]
    config_schema = ContentGenConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ContentGenConfig = config
        topic = Topic.model_validate(inputs["selected_topic"])
        materials = [Material.model_validate(m) for m in inputs.get("materials", [])]

        # Get platform rules for the prompt
        try:
            platform = get_platform(cfg.platform)
            platform_rules = platform.get_rules_prompt()
        except ValueError:
            platform_rules = f"Platform: {cfg.platform}"

        prompt = self.load_prompt(
            "generate.j2",
            platform=cfg.platform,
            format=cfg.format,
            topic_title=topic.title,
            topic_angle=topic.angle,
            materials=[m.model_dump() for m in materials],
            platform_rules=platform_rules,
            style=cfg.style,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_content = json.loads(response.strip())
            if not isinstance(raw_content, dict):
                raise ValueError("Expected a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Failed to parse content generation response: {e}") from e

        content = PlatformContent(
            platform=cfg.platform,
            title=raw_content.get("title", ""),
            body=raw_content.get("body", ""),
            tags=raw_content.get("tags", []),
            image_paths=[],
            image_prompts=raw_content.get("image_prompts", []),
        )

        # Merge with existing contents if any
        return {"contents": {cfg.platform: content.model_dump()}}
```

- [ ] **Step 6: Write __init__.py**

```python
# server/src/agents/content_generator/__init__.py
from src.agents.content_generator.agent import ContentGeneratorAgent
__all__ = ["ContentGeneratorAgent"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd server && python -m pytest tests/agents/test_content_generator.py -v`
Expected: All 2 tests PASS

- [ ] **Step 8: Commit**

```bash
git add server/src/agents/content_generator/ server/tests/agents/test_content_generator.py
git commit -m "feat: add Content Generator Agent"
```

---

### Task 13: Reviewer Agent

**Files:**
- Create: `server/src/agents/reviewer/__init__.py`
- Create: `server/src/agents/reviewer/agent.py`
- Create: `server/src/agents/reviewer/schemas.py`
- Create: `server/src/agents/reviewer/prompts/review.j2`
- Create: `server/tests/agents/test_reviewer.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/agents/test_reviewer.py
import pytest
import json
from unittest.mock import AsyncMock
from src.agents.reviewer.agent import ReviewerAgent
from src.agents.reviewer.schemas import ReviewerConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "score": 8.5,
        "issues": [],
        "suggestions": ["可以增加更多数据支撑"],
    }))
    return model


def test_reviewer_metadata():
    assert ReviewerAgent.name == "reviewer"
    assert ReviewerAgent.consumes == ["contents"]
    assert ReviewerAgent.produces == ["reviews"]


@pytest.mark.asyncio
async def test_reviewer_passes_good_content(mock_model):
    agent = ReviewerAgent(model=mock_model)
    config = ReviewerConfig(min_score=7.0)
    inputs = {
        "contents": {
            "xiaohongshu": {
                "platform": "xiaohongshu",
                "title": "Good Title",
                "body": "A well written article about AI tools that meets all requirements.",
                "tags": ["AI"],
                "image_paths": [],
            }
        }
    }

    result = await agent.run(inputs, config)

    assert "reviews" in result
    assert "xiaohongshu" in result["reviews"]
    review = result["reviews"]["xiaohongshu"]
    assert review["passed"] is True
    assert review["score"] == 8.5


@pytest.mark.asyncio
async def test_reviewer_fails_low_score(mock_model):
    mock_model.generate = AsyncMock(return_value=json.dumps({
        "score": 4.0,
        "issues": ["内容质量不足"],
        "suggestions": ["重写"],
    }))
    agent = ReviewerAgent(model=mock_model)
    config = ReviewerConfig(min_score=7.0)
    inputs = {
        "contents": {
            "xiaohongshu": {
                "platform": "xiaohongshu",
                "title": "Bad",
                "body": "Short",
                "tags": [],
                "image_paths": [],
            }
        }
    }

    result = await agent.run(inputs, config)
    review = result["reviews"]["xiaohongshu"]
    assert review["passed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/agents/test_reviewer.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write schemas.py**

```python
# server/src/agents/reviewer/schemas.py
from pydantic import BaseModel, Field


class ReviewerConfig(BaseModel):
    rules: list[str] = Field(default=["quality_score"], description="Review rule names")
    min_score: float = Field(default=7.0, description="Minimum score to pass")
    temperature: float = Field(default=0.3, description="Low temp for consistent reviews")
```

- [ ] **Step 4: Write the prompt template**

```jinja2
{# server/src/agents/reviewer/prompts/review.j2 #}
你是一个专业的内容审核专家。请审核以下「{{ platform }}」平台的内容。

## 内容
标题：{{ title }}

正文：
{{ body }}

标签：{{ tags | join(', ') }}

## 平台规则
{{ platform_rules }}

## 审核维度
{% for rule in rules %}
- {{ rule }}
{% endfor %}

## 输出格式
JSON 对象：
```json
{
  "score": 8.5,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1"]
}
```

评分标准（0-10）：
- 9-10：优秀，直接发布
- 7-8：良好，小调整后可发布
- 5-6：一般，需要较大修改
- 0-4：不合格，需要重写

只输出 JSON 对象，不要其他内容。
```

- [ ] **Step 5: Write agent.py**

```python
# server/src/agents/reviewer/agent.py
"""Reviewer Agent — AI-powered content quality review."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.reviewer.schemas import ReviewerConfig
from src.core.state import PlatformContent, ReviewResult
from src.platforms.base import get_platform


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    consumes = ["contents"]
    produces = ["reviews"]
    config_schema = ReviewerConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ReviewerConfig = config
        contents: dict[str, dict] = inputs.get("contents", {})
        reviews: dict[str, dict] = {}

        for platform_name, content_data in contents.items():
            content = PlatformContent.model_validate(content_data)

            # Platform validation (rule-based)
            try:
                platform = get_platform(platform_name)
                platform_issues = platform.validate(content_data)
                platform_rules = platform.get_rules_prompt()
            except ValueError:
                platform_issues = []
                platform_rules = ""

            # LLM review
            prompt = self.load_prompt(
                "review.j2",
                platform=platform_name,
                title=content.title,
                body=content.body,
                tags=content.tags,
                platform_rules=platform_rules,
                rules=cfg.rules,
            )

            response = await self.model.generate(prompt, temperature=cfg.temperature)

            try:
                raw_review = json.loads(response.strip())
            except (json.JSONDecodeError, ValueError):
                raw_review = {"score": 0.0, "issues": ["Failed to parse review"], "suggestions": []}

            score = raw_review.get("score", 0.0)
            all_issues = platform_issues + raw_review.get("issues", [])
            passed = score >= cfg.min_score and len(platform_issues) == 0

            review = ReviewResult(
                platform=platform_name,
                passed=passed,
                score=score,
                issues=all_issues,
                suggestions=raw_review.get("suggestions", []),
            )
            reviews[platform_name] = review.model_dump()

        return {"reviews": reviews}
```

- [ ] **Step 6: Write __init__.py**

```python
# server/src/agents/reviewer/__init__.py
from src.agents.reviewer.agent import ReviewerAgent
__all__ = ["ReviewerAgent"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd server && python -m pytest tests/agents/test_reviewer.py -v`
Expected: All 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add server/src/agents/reviewer/ server/tests/agents/test_reviewer.py
git commit -m "feat: add Reviewer Agent with platform + LLM review"
```

---

### Task 14: Analyst Agent (post-publish analytics)

**Files:**
- Create: `server/src/agents/analyst/__init__.py`
- Create: `server/src/agents/analyst/agent.py`
- Create: `server/src/agents/analyst/schemas.py`
- Create: `server/src/agents/analyst/prompts/analyze.j2`
- Create: `server/tests/agents/test_analyst.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/agents/test_analyst.py
import pytest
import json
from unittest.mock import AsyncMock
from src.agents.analyst.agent import AnalystAgent
from src.agents.analyst.schemas import AnalystConfig


@pytest.fixture
def mock_model():
    model = AsyncMock()
    model.generate = AsyncMock(return_value=json.dumps({
        "summary": "本次内容整体质量良好",
        "insights": ["AI工具类内容受众广", "对比形式效果好"],
        "improvement_suggestions": ["增加实际使用截图", "加入价格对比"],
    }))
    return model


def test_analyst_metadata():
    assert AnalystAgent.name == "analyst"
    assert "contents" in AnalystAgent.consumes
    assert "reviews" in AnalystAgent.consumes
    assert AnalystAgent.produces == ["analysis"]


@pytest.mark.asyncio
async def test_analyst_run(mock_model):
    agent = AnalystAgent(model=mock_model)
    config = AnalystConfig(metrics=["engagement", "reach"])
    inputs = {
        "contents": {"xiaohongshu": {"platform": "xiaohongshu", "title": "Test", "body": "Body", "tags": []}},
        "reviews": {"xiaohongshu": {"platform": "xiaohongshu", "passed": True, "score": 8.0, "issues": [], "suggestions": []}},
    }

    result = await agent.run(inputs, config)

    assert "analysis" in result
    assert result["analysis"]["summary"] == "本次内容整体质量良好"
    assert len(result["analysis"]["insights"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/agents/test_analyst.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write schemas.py**

```python
# server/src/agents/analyst/schemas.py
from pydantic import BaseModel, Field


class AnalystConfig(BaseModel):
    metrics: list[str] = Field(default=["engagement", "reach"], description="Metrics to analyze")
    temperature: float = Field(default=0.5)
```

- [ ] **Step 4: Write the prompt template**

```jinja2
{# server/src/agents/analyst/prompts/analyze.j2 #}
你是一个专业的内容运营分析师。请对本次内容生产进行复盘分析。

## 生成的内容
{% for platform, content in contents.items() %}
### {{ platform }}
标题：{{ content.title }}
正文摘要：{{ content.body[:200] }}
标签：{{ content.tags | join(', ') if content.tags else '无' }}
{% endfor %}

## 审核结果
{% for platform, review in reviews.items() %}
### {{ platform }}
- 通过：{{ '是' if review.passed else '否' }}
- 评分：{{ review.score }}
{% if review.issues %}- 问题：{{ review.issues | join(', ') }}{% endif %}
{% if review.suggestions %}- 建议：{{ review.suggestions | join(', ') }}{% endif %}
{% endfor %}

## 分析维度
{% for metric in metrics %}
- {{ metric }}
{% endfor %}

## 输出格式
```json
{
  "summary": "整体分析总结",
  "insights": ["洞察1", "洞察2"],
  "improvement_suggestions": ["改进建议1", "改进建议2"]
}
```

只输出 JSON 对象，不要其他内容。
```

- [ ] **Step 5: Write agent.py**

```python
# server/src/agents/analyst/agent.py
"""Analyst Agent — post-publish analytics and improvement suggestions."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.analyst.schemas import AnalystConfig
from src.core.state import Analysis


class AnalystAgent(BaseAgent):
    name = "analyst"
    consumes = ["contents", "reviews"]
    produces = ["analysis"]
    config_schema = AnalystConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: AnalystConfig = config

        prompt = self.load_prompt(
            "analyze.j2",
            contents=inputs.get("contents", {}),
            reviews=inputs.get("reviews", {}),
            metrics=cfg.metrics,
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw_analysis = json.loads(response.strip())
        except (json.JSONDecodeError, ValueError):
            raw_analysis = {
                "summary": "Analysis failed to parse",
                "insights": [],
                "improvement_suggestions": [],
            }

        analysis = Analysis.model_validate(raw_analysis)
        return {"analysis": analysis.model_dump()}
```

- [ ] **Step 6: Write __init__.py**

```python
# server/src/agents/analyst/__init__.py
from src.agents.analyst.agent import AnalystAgent
__all__ = ["AnalystAgent"]
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd server && python -m pytest tests/agents/test_analyst.py -v`
Expected: All 2 tests PASS

- [ ] **Step 8: Commit**

```bash
git add server/src/agents/analyst/ server/tests/agents/test_analyst.py
git commit -m "feat: add Analyst Agent for post-publish review"
```

---

## Phase 3: CLI Interface

### Task 15: CLI app entry point and `sp pipeline` commands

**Files:**
- Create: `server/src/cli/app.py`
- Create: `server/src/cli/commands/pipeline.py`
- Create: `server/src/cli/formatters.py`
- Create: `server/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_cli.py
import pytest
from typer.testing import CliRunner
from pathlib import Path
from src.cli.app import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "SuperPipeline" in result.stdout or "sp" in result.stdout


def test_pipeline_list(tmp_path, monkeypatch):
    # Create a test pipeline
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test.yaml").write_text("name: Test Pipeline\nstages: []")
    monkeypatch.setenv("SP_PIPELINES_DIR", str(pipelines_dir))

    result = runner.invoke(app, ["pipeline", "list"])
    assert result.exit_code == 0
    assert "Test Pipeline" in result.stdout


def test_pipeline_list_json(tmp_path, monkeypatch):
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "test.yaml").write_text("name: Test\nstages: []")
    monkeypatch.setenv("SP_PIPELINES_DIR", str(pipelines_dir))

    result = runner.invoke(app, ["pipeline", "list", "--format", "json"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert isinstance(data, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_cli.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write formatters.py**

```python
# server/src/cli/formatters.py
"""Output formatters for CLI commands."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def output(data: Any, fmt: str = "table", columns: list[str] | None = None) -> None:
    """Format and print data based on requested format."""
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
```

- [ ] **Step 4: Write pipeline commands**

```python
# server/src/cli/commands/pipeline.py
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
    return Path(__file__).parent.parent.parent / "pipelines"


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
    data = config.model_dump()
    output(data, fmt)
```

- [ ] **Step 5: Write CLI app entry**

```python
# server/src/cli/app.py
"""SuperPipeline CLI — main entry point."""

from __future__ import annotations

import typer

from src.cli.commands import pipeline as pipeline_cmd

app = typer.Typer(
    name="sp",
    help="SuperPipeline — Multi-agent content production pipeline",
    no_args_is_help=True,
)

app.add_typer(pipeline_cmd.app, name="pipeline")


if __name__ == "__main__":
    app()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_cli.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add server/src/cli/ server/tests/test_cli.py
git commit -m "feat: add CLI entry point with pipeline list/show commands"
```

---

### Task 16: CLI `sp run` and `sp status` commands

**Files:**
- Create: `server/src/cli/commands/run.py`
- Create: `server/src/cli/commands/status.py`
- Modify: `server/src/cli/app.py` — add new command groups
- Create: `server/src/core/engine.py` — high-level engine facade
- Create: `server/tests/test_cli_run.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_cli_run.py
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.run._run_pipeline")
def test_sp_run_returns_run_id(mock_run):
    mock_run.return_value = {"run_id": "abc123", "status": "completed"}

    result = runner.invoke(app, ["run", "xiaohongshu_image_text", "--brief", "AI tools review", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["run_id"] == "abc123"


@patch("src.cli.commands.status._get_run_status")
def test_sp_status_list(mock_status):
    mock_status.return_value = [
        {"run_id": "abc123", "pipeline_name": "test", "status": "completed", "created_at": "2026-04-15"},
    ]

    result = runner.invoke(app, ["status", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1


@patch("src.cli.commands.status._get_run_detail")
def test_sp_status_single_run(mock_detail):
    mock_detail.return_value = {
        "run_id": "abc123",
        "pipeline_name": "test",
        "status": "completed",
        "stage": "completed",
    }

    result = runner.invoke(app, ["status", "abc123", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["run_id"] == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_cli_run.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write engine.py (high-level facade)**

```python
# server/src/core/engine.py
"""High-level engine facade — wires together all components."""

from __future__ import annotations

from pathlib import Path

from src.core.config import AppConfig, load_config
from src.core.models import create_model_adapter, ModelAdapter
from src.core.orchestrator import Orchestrator
from src.core.pipeline_loader import load_pipeline, list_pipelines
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, UserBrief
from src.storage.state_store import StateStore
from src.storage.asset_store import AssetStore


class Engine:
    """Top-level facade that ties config, registry, storage, and orchestrator together."""

    def __init__(self, config: AppConfig, pipelines_dir: Path) -> None:
        self.config = config
        self.pipelines_dir = pipelines_dir
        self.text_model: ModelAdapter = create_model_adapter(config.models.text)
        self.registry = AgentRegistry()
        self.orchestrator = Orchestrator(self.registry)
        self.state_store = StateStore(config.storage.db_path)
        self.asset_store = AssetStore(config.storage.assets_dir, config.storage.outputs_dir)

    async def initialize(self) -> None:
        """Initialize storage and register all agents."""
        await self.state_store.initialize()
        self._register_agents()

    def _register_agents(self) -> None:
        """Import and register all agent modules."""
        from src.agents.topic_generator import TopicGeneratorAgent
        from src.agents.material_collector import MaterialCollectorAgent
        from src.agents.content_generator import ContentGeneratorAgent
        from src.agents.reviewer import ReviewerAgent
        from src.agents.analyst import AnalystAgent

        for agent_cls in [TopicGeneratorAgent, MaterialCollectorAgent, ContentGeneratorAgent, ReviewerAgent, AnalystAgent]:
            self.registry.register(agent_cls, model=self.text_model)

    def load_pipeline(self, name: str) -> PipelineConfig:
        """Load a pipeline config by name."""
        yaml_file = self.pipelines_dir / f"{name}.yaml"
        return load_pipeline(yaml_file)

    async def run_pipeline(self, pipeline_name: str, brief: UserBrief) -> dict:
        """Run a pipeline end-to-end."""
        pipeline_config = self.load_pipeline(pipeline_name)

        # Save run to DB
        import uuid
        run_id = uuid.uuid4().hex[:12]
        await self.state_store.save_run(run_id, pipeline_name, "running", {})

        try:
            result = await self.orchestrator.run(pipeline_config, brief, run_id=run_id)

            # Persist contents to DB
            for platform, content_data in result.get("contents", {}).items():
                content_id = f"{run_id}-{platform}"
                review = result.get("reviews", {}).get(platform, {})
                status = "approved" if review.get("passed", False) else "pending_review"
                await self.state_store.save_content(
                    content_id=content_id,
                    run_id=run_id,
                    platform=platform,
                    title=content_data.get("title", ""),
                    body=content_data.get("body", ""),
                    status=status,
                    tags=content_data.get("tags", []),
                    image_paths=content_data.get("image_paths", []),
                )

            await self.state_store.update_run(run_id, status=result.get("stage", "completed"), state=result)
            return {"run_id": run_id, "status": result.get("stage", "completed"), **result}

        except Exception as e:
            await self.state_store.update_run(run_id, status="failed", state={"error": str(e)})
            return {"run_id": run_id, "status": "failed", "error": str(e)}

    async def close(self) -> None:
        await self.state_store.close()
        await self.text_model.close()
```

- [ ] **Step 4: Write run command**

```python
# server/src/cli/commands/run.py
"""CLI command: sp run <pipeline> --brief "..."."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.core.engine import Engine
from src.core.state import UserBrief

app = typer.Typer(help="Run a pipeline")


def _get_config_path() -> Path:
    return Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))


def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent / "pipelines"


def _run_pipeline(pipeline_name: str, brief_text: str) -> dict:
    """Sync wrapper for async pipeline run."""
    config = load_config(_get_config_path())
    engine = Engine(config, _get_pipelines_dir())

    async def _execute():
        await engine.initialize()
        brief = UserBrief(topic=brief_text)
        result = await engine.run_pipeline(pipeline_name, brief)
        await engine.close()
        return result

    return asyncio.run(_execute())


@app.callback(invoke_without_command=True)
def run(
    pipeline: str = typer.Argument(help="Pipeline name (YAML filename without extension)"),
    brief: str = typer.Option("", "--brief", "-b", help="Topic/brief text"),
    brief_file: str = typer.Option("", "--brief-file", help="Path to brief JSON file"),
    fmt: str = typer.Option("table", "--format", help="Output format: json, table, plain"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Wait for completion"),
) -> None:
    """Run a content production pipeline."""
    if not brief and not brief_file:
        typer.echo("Error: Provide --brief or --brief-file", err=True)
        raise typer.Exit(code=2)

    brief_text = brief
    if brief_file:
        brief_data = json.loads(Path(brief_file).read_text())
        brief_text = brief_data.get("topic", brief_data.get("brief", ""))

    try:
        result = _run_pipeline(pipeline, brief_text)
        output({"run_id": result["run_id"], "status": result["status"]}, fmt)
        raise typer.Exit(code=0 if result["status"] == "completed" else 3)
    except FileNotFoundError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=4)
```

- [ ] **Step 5: Write status command**

```python
# server/src/cli/commands/status.py
"""CLI command: sp status [run_id]."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

import typer

from src.cli.formatters import output
from src.core.config import load_config
from src.storage.state_store import StateStore

app = typer.Typer(help="Check pipeline run status")


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)


def _get_run_status(limit: int = 20) -> list[dict]:
    store = _get_store()

    async def _fetch():
        await store.initialize()
        runs = await store.list_runs(limit=limit)
        await store.close()
        return runs

    return asyncio.run(_fetch())


def _get_run_detail(run_id: str) -> dict | None:
    store = _get_store()

    async def _fetch():
        await store.initialize()
        run = await store.get_run(run_id)
        await store.close()
        return run

    return asyncio.run(_fetch())


@app.callback(invoke_without_command=True)
def status(
    run_id: Optional[str] = typer.Argument(None, help="Specific run ID to check"),
    fmt: str = typer.Option("table", "--format", help="Output format: json, table, plain"),
    stage: Optional[str] = typer.Option(None, "--stage", help="Show specific stage details"),
) -> None:
    """Check pipeline run status."""
    if run_id:
        run = _get_run_detail(run_id)
        if run is None:
            typer.echo(f"Run '{run_id}' not found", err=True)
            raise typer.Exit(code=4)
        if stage and "state" in run:
            # Show specific stage output from state
            state = run.get("state", {})
            output({"stage": stage, "data": state.get(stage, "No data for this stage")}, fmt)
        else:
            output(run, fmt)
    else:
        runs = _get_run_status()
        output(runs, fmt, columns=["run_id", "pipeline_name", "status", "created_at"])
```

- [ ] **Step 6: Update app.py to add new commands**

```python
# server/src/cli/app.py
"""SuperPipeline CLI — main entry point."""

from __future__ import annotations

import typer

from src.cli.commands import pipeline as pipeline_cmd
from src.cli.commands import run as run_cmd
from src.cli.commands import status as status_cmd

app = typer.Typer(
    name="sp",
    help="SuperPipeline — Multi-agent content production pipeline",
    no_args_is_help=True,
)

app.add_typer(pipeline_cmd.app, name="pipeline")
app.add_typer(run_cmd.app, name="run")
app.add_typer(status_cmd.app, name="status")


if __name__ == "__main__":
    app()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_cli_run.py -v`
Expected: All 3 tests PASS

- [ ] **Step 8: Commit**

```bash
git add server/src/cli/ server/src/core/engine.py server/tests/test_cli_run.py
git commit -m "feat: add sp run and sp status CLI commands with engine facade"
```

---

### Task 17: CLI `sp content` commands

**Files:**
- Create: `server/src/cli/commands/content.py`
- Modify: `server/src/cli/app.py` — add content command group
- Create: `server/tests/test_cli_content.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_cli_content.py
import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.content._list_contents")
def test_content_list(mock_list):
    mock_list.return_value = [
        {"content_id": "c1", "platform": "xiaohongshu", "title": "Test", "status": "approved"},
    ]
    result = runner.invoke(app, ["content", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1


@patch("src.cli.commands.content._get_content")
def test_content_get(mock_get):
    mock_get.return_value = {
        "content_id": "c1",
        "platform": "xiaohongshu",
        "title": "AI Tools",
        "body": "Full content body here",
        "status": "approved",
    }
    result = runner.invoke(app, ["content", "get", "c1", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["content_id"] == "c1"


@patch("src.cli.commands.content._get_content")
def test_content_get_copy_mode(mock_get):
    mock_get.return_value = {
        "content_id": "c1",
        "title": "Title",
        "body": "Body text for copy",
        "tags": ["AI"],
    }
    result = runner.invoke(app, ["content", "get", "c1", "--copy"])
    assert result.exit_code == 0
    assert "Title" in result.stdout
    assert "Body text for copy" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_cli_content.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write content command**

```python
# server/src/cli/commands/content.py
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
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)


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
        # Plain text output for pipe/copy
        console.print(f"{content.get('title', '')}\n")
        console.print(content.get("body", ""))
        tags = content.get("tags", [])
        if tags:
            console.print(f"\n{'  '.join(f'#{t}' for t in tags)}")
    else:
        output(content, fmt)


@app.command("approve")
def content_approve(
    content_id: str = typer.Argument(help="Content ID to approve/mark published"),
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
```

- [ ] **Step 4: Update app.py**

```python
# server/src/cli/app.py
"""SuperPipeline CLI — main entry point."""

from __future__ import annotations

import typer

from src.cli.commands import pipeline as pipeline_cmd
from src.cli.commands import run as run_cmd
from src.cli.commands import status as status_cmd
from src.cli.commands import content as content_cmd

app = typer.Typer(
    name="sp",
    help="SuperPipeline — Multi-agent content production pipeline",
    no_args_is_help=True,
)

app.add_typer(pipeline_cmd.app, name="pipeline")
app.add_typer(run_cmd.app, name="run")
app.add_typer(status_cmd.app, name="status")
app.add_typer(content_cmd.app, name="content")


if __name__ == "__main__":
    app()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_cli_content.py -v`
Expected: All 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/src/cli/ server/tests/test_cli_content.py
git commit -m "feat: add sp content list/get/approve CLI commands"
```

---

### Task 18: CLI `sp agent` commands

**Files:**
- Create: `server/src/cli/commands/agent.py`
- Modify: `server/src/cli/app.py` — add agent command group
- Create: `server/tests/test_cli_agent.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_cli_agent.py
import pytest
import json
from unittest.mock import patch
from typer.testing import CliRunner
from src.cli.app import app

runner = CliRunner()


@patch("src.cli.commands.agent._list_agents")
def test_agent_list(mock_list):
    mock_list.return_value = [
        {"name": "topic_generator", "consumes": ["user_brief"], "produces": ["topics", "selected_topic"], "config_schema": "TopicGenConfig"},
    ]
    result = runner.invoke(app, ["agent", "list", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["name"] == "topic_generator"


@patch("src.cli.commands.agent._list_agents")
def test_agent_list_table(mock_list):
    mock_list.return_value = [
        {"name": "topic_generator", "consumes": ["user_brief"], "produces": ["topics"], "config_schema": "TopicGenConfig"},
    ]
    result = runner.invoke(app, ["agent", "list"])
    assert result.exit_code == 0
    assert "topic_generator" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_cli_agent.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write agent command**

```python
# server/src/cli/commands/agent.py
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
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    pipelines_dir = Path(os.environ.get("SP_PIPELINES_DIR", Path(__file__).parent.parent.parent / "pipelines"))
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
    fmt: str = typer.Option("table", "--format", help="Output format: json, table, plain"),
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
```

- [ ] **Step 4: Update app.py to add agent commands**

Add to `server/src/cli/app.py`:
```python
from src.cli.commands import agent as agent_cmd
app.add_typer(agent_cmd.app, name="agent")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_cli_agent.py -v`
Expected: All 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add server/src/cli/commands/agent.py server/tests/test_cli_agent.py server/src/cli/app.py
git commit -m "feat: add sp agent list/run CLI commands"
```

---

## Phase 4: API Layer + Web UI

### Task 19: FastAPI app with pipeline, content, and runs routes

**Files:**
- Create: `server/src/api/app.py`
- Create: `server/src/api/routes/pipelines.py`
- Create: `server/src/api/routes/contents.py`
- Create: `server/src/api/schemas.py`
- Create: `server/src/api/sse.py`
- Create: `server/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# server/tests/test_api.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport
from src.api.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
@patch("src.api.routes.pipelines._list_pipelines")
async def test_list_pipelines_api(mock_list, client):
    mock_list.return_value = [{"name": "test", "stages": 3}]
    response = await client.get("/api/pipelines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
@patch("src.api.routes.contents._list_contents")
async def test_list_contents_api(mock_list, client):
    mock_list.return_value = [
        {"content_id": "c1", "platform": "xiaohongshu", "title": "Test", "status": "approved"}
    ]
    response = await client.get("/api/contents")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
@patch("src.api.routes.runs._list_runs")
async def test_list_runs_api(mock_list, client):
    mock_list.return_value = [
        {"run_id": "abc123", "pipeline_name": "test", "status": "completed", "created_at": "2026-04-15"}
    ]
    response = await client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "abc123"


@pytest.mark.asyncio
@patch("src.api.routes.runs._get_run")
async def test_get_run_api(mock_get, client):
    mock_get.return_value = {"run_id": "abc123", "status": "completed", "state": {}}
    response = await client.get("/api/runs/abc123")
    assert response.status_code == 200
    assert response.json()["run_id"] == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_api.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Write API schemas**

```python
# server/src/api/schemas.py
"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RunPipelineRequest(BaseModel):
    pipeline: str = Field(description="Pipeline name")
    brief: str = Field(description="Topic/brief text")
    keywords: list[str] = Field(default_factory=list)
    platform_hints: list[str] = Field(default_factory=list)


class RunPipelineResponse(BaseModel):
    run_id: str
    status: str


class ContentResponse(BaseModel):
    content_id: str
    run_id: str
    platform: str
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    status: str
    created_at: str = ""


class ApproveRequest(BaseModel):
    publish_url: str = ""
```

- [ ] **Step 4: Write pipeline routes**

```python
# server/src/api/routes/pipelines.py
"""API routes for pipeline operations."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter

from src.core.pipeline_loader import list_pipelines

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def _get_pipelines_dir() -> Path:
    env_dir = os.environ.get("SP_PIPELINES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).parent.parent.parent / "pipelines"


def _list_pipelines() -> list[dict]:
    return list_pipelines(_get_pipelines_dir())


@router.get("")
async def get_pipelines():
    """List all available pipelines."""
    return _list_pipelines()
```

- [ ] **Step 5: Write content routes**

```python
# server/src/api/routes/contents.py
"""API routes for content operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas import ApproveRequest
from src.core.config import load_config
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/contents", tags=["contents"])


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)


async def _list_contents(status: str | None = None, run_id: str | None = None) -> list[dict]:
    store = _get_store()
    await store.initialize()
    contents = await store.list_contents(status=status, run_id=run_id)
    await store.close()
    return contents


@router.get("")
async def get_contents(status: Optional[str] = None, run_id: Optional[str] = None):
    """List contents with optional filters."""
    return await _list_contents(status=status, run_id=run_id)


@router.get("/{content_id}")
async def get_content(content_id: str):
    """Get a single content by ID."""
    store = _get_store()
    await store.initialize()
    content = await store.get_content(content_id)
    await store.close()
    if content is None:
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    return content


@router.post("/{content_id}/approve")
async def approve_content(content_id: str, body: ApproveRequest):
    """Mark content as published."""
    store = _get_store()
    await store.initialize()
    content = await store.get_content(content_id)
    if content is None:
        await store.close()
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    updates = {"status": "published"}
    if body.publish_url:
        updates["publish_url"] = body.publish_url
    await store.update_content(content_id, **updates)
    await store.close()
    return {"message": "Content marked as published", "content_id": content_id}
```

- [ ] **Step 6: Write runs routes**

```python
# server/src/api/routes/runs.py
"""API routes for pipeline run operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from src.core.config import load_config
from src.storage.state_store import StateStore

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _get_store() -> StateStore:
    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent.parent.parent / "config.yaml"))
    config = load_config(config_path)
    return StateStore(config.storage.db_path)


async def _list_runs(limit: int = 20, status: str | None = None) -> list[dict]:
    store = _get_store()
    await store.initialize()
    runs = await store.list_runs(limit=limit, status=status)
    await store.close()
    return runs


async def _get_run(run_id: str) -> dict | None:
    store = _get_store()
    await store.initialize()
    run = await store.get_run(run_id)
    await store.close()
    return run


@router.get("")
async def get_runs(limit: int = 20, status: Optional[str] = None):
    """List pipeline runs."""
    return await _list_runs(limit=limit, status=status)


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Get a single run by ID."""
    run = await _get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run
```

- [ ] **Step 7: Write SSE endpoint**

```python
# server/src/api/sse.py
"""Server-Sent Events for real-time pipeline status updates."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["sse"])

# Simple in-memory event bus for MVP
_event_queues: dict[str, list[asyncio.Queue]] = {}


def publish_event(run_id: str, event: dict) -> None:
    """Publish an event to all subscribers of a run."""
    for queue in _event_queues.get(run_id, []):
        queue.put_nowait(event)


async def _event_stream(run_id: str) -> AsyncGenerator[dict, None]:
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues.setdefault(run_id, []).append(queue)
    try:
        while True:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield {"event": event.get("type", "update"), "data": json.dumps(event)}
            if event.get("type") == "pipeline_completed":
                break
    except asyncio.TimeoutError:
        yield {"event": "keepalive", "data": "{}"}
    finally:
        _event_queues.get(run_id, []).remove(queue)


@router.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    """SSE stream for pipeline run events."""
    return EventSourceResponse(_event_stream(run_id))
```

- [ ] **Step 8: Write FastAPI app**

```python
# server/src/api/app.py
"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import pipelines, contents, runs
from src.api import sse


def create_app() -> FastAPI:
    app = FastAPI(
        title="SuperPipeline API",
        description="Multi-agent content production pipeline",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(pipelines.router)
    app.include_router(contents.router)
    app.include_router(runs.router)
    app.include_router(sse.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
```

- [ ] **Step 9: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 10: Commit**

```bash
git add server/src/api/ server/tests/test_api.py
git commit -m "feat: add FastAPI with pipeline, content, and SSE endpoints"
```

---

### Task 20: Next.js Web UI scaffold

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`
- Create: `web/src/lib/api-client.ts`
- Create: `web/src/lib/types.ts`
- Create: `web/src/components/RunList.tsx`
- Create: `web/src/components/ContentCard.tsx`
- Create: `web/src/components/PipelineGraph.tsx`
- Create: `web/src/app/runs/[runId]/page.tsx`
- Create: `web/src/app/contents/page.tsx`

- [ ] **Step 1: Initialize Next.js project**

Run: `cd web && npx create-next-app@latest . --typescript --tailwind --app --src-dir --no-eslint --import-alias "@/*" --use-npm`

If the directory already exists, run from the repo root:
```bash
npx create-next-app@latest web --typescript --tailwind --app --src-dir --no-eslint --import-alias "@/*" --use-npm
```

- [ ] **Step 2: Write types.ts**

```typescript
// web/src/lib/types.ts
export interface PipelineRun {
  run_id: string;
  pipeline_name: string;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface Content {
  content_id: string;
  run_id: string;
  platform: string;
  title: string;
  body: string;
  tags: string[];
  status: "pending_review" | "approved" | "rejected" | "published";
  created_at: string;
}

export interface PipelineStage {
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
  output_summary?: string;
}

export interface PipelineEvent {
  type: "stage_started" | "stage_completed" | "stage_failed" | "pipeline_completed";
  agent?: string;
  timestamp: string;
  output_summary?: string;
  error?: string;
}
```

- [ ] **Step 3: Write api-client.ts**

```typescript
// web/src/lib/api-client.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  listRuns: () => fetchApi<any[]>("/api/runs"),
  getRun: (runId: string) => fetchApi<any>(`/api/runs/${runId}`),
  listContents: (params?: { status?: string; run_id?: string }) => {
    const search = new URLSearchParams();
    if (params?.status) search.set("status", params.status);
    if (params?.run_id) search.set("run_id", params.run_id);
    const qs = search.toString();
    return fetchApi<any[]>(`/api/contents${qs ? `?${qs}` : ""}`);
  },
  getContent: (id: string) => fetchApi<any>(`/api/contents/${id}`),
  approveContent: (id: string, publishUrl?: string) =>
    fetchApi<any>(`/api/contents/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ publish_url: publishUrl || "" }),
    }),
};
```

- [ ] **Step 4: Write RunList component**

```tsx
// web/src/components/RunList.tsx
"use client";

import Link from "next/link";

interface Run {
  run_id: string;
  pipeline_name: string;
  status: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-800",
  running: "bg-blue-100 text-blue-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-800",
};

export function RunList({ runs }: { runs: Run[] }) {
  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <Link
          key={run.run_id}
          href={`/runs/${run.run_id}`}
          className="block p-4 border rounded-lg hover:bg-gray-50"
        >
          <div className="flex justify-between items-center">
            <div>
              <span className="font-mono text-sm text-gray-500">{run.run_id}</span>
              <span className="ml-2 font-medium">{run.pipeline_name}</span>
            </div>
            <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[run.status] || ""}`}>
              {run.status}
            </span>
          </div>
          <div className="text-xs text-gray-400 mt-1">{run.created_at}</div>
        </Link>
      ))}
    </div>
  );
}
```

- [ ] **Step 5: Write ContentCard component**

```tsx
// web/src/components/ContentCard.tsx
"use client";

import { useState } from "react";

interface ContentCardProps {
  content: {
    content_id: string;
    platform: string;
    title: string;
    body: string;
    tags: string[];
    status: string;
  };
}

export function ContentCard({ content }: ContentCardProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    const text = `${content.title}\n\n${content.body}\n\n${content.tags.map((t) => `#${t}`).join(" ")}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex justify-between items-start">
        <div>
          <span className="text-xs font-medium px-2 py-0.5 bg-blue-100 text-blue-800 rounded">
            {content.platform}
          </span>
          <span className="ml-2 text-xs text-gray-400">{content.status}</span>
        </div>
        <button
          onClick={copyToClipboard}
          className="px-3 py-1 text-sm bg-gray-900 text-white rounded hover:bg-gray-700"
        >
          {copied ? "✓ Copied" : "Copy"}
        </button>
      </div>
      <h3 className="font-medium">{content.title}</h3>
      <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-6">{content.body}</p>
      {content.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {content.tags.map((tag) => (
            <span key={tag} className="text-xs text-blue-600">#{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 6: Write PipelineGraph component**

```tsx
// web/src/components/PipelineGraph.tsx
"use client";

interface Stage {
  agent: string;
  status: "pending" | "running" | "completed" | "failed";
}

const STATUS_ICONS: Record<string, string> = {
  pending: "⏳",
  running: "🔄",
  completed: "✅",
  failed: "❌",
};

export function PipelineGraph({ stages }: { stages: Stage[] }) {
  return (
    <div className="flex items-center gap-2 overflow-x-auto py-4">
      {stages.map((stage, i) => (
        <div key={stage.agent} className="flex items-center">
          <div
            className={`px-4 py-3 rounded-lg border-2 text-center min-w-[120px] ${
              stage.status === "running" ? "border-blue-500 bg-blue-50" :
              stage.status === "completed" ? "border-green-500 bg-green-50" :
              stage.status === "failed" ? "border-red-500 bg-red-50" :
              "border-gray-300 bg-gray-50"
            }`}
          >
            <div className="text-lg">{STATUS_ICONS[stage.status]}</div>
            <div className="text-xs font-medium mt-1">{stage.agent}</div>
          </div>
          {i < stages.length - 1 && <div className="text-gray-300 mx-1">→</div>}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Write dashboard page**

```tsx
// web/src/app/page.tsx
import { RunList } from "@/components/RunList";

export default function Dashboard() {
  // In MVP, this is a static placeholder. Data fetching added when API is connected.
  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">SuperPipeline</h1>
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Recent Runs</h2>
        <RunList runs={[]} />
        <p className="text-sm text-gray-400 mt-2">Connect API to see runs</p>
      </section>
    </main>
  );
}
```

- [ ] **Step 8: Write layout**

```tsx
// web/src/app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SuperPipeline",
  description: "Content production pipeline dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className="bg-white text-gray-900">{children}</body>
    </html>
  );
}
```

- [ ] **Step 9: Write runs/[runId] page**

```tsx
// web/src/app/runs/[runId]/page.tsx
import { PipelineGraph } from "@/components/PipelineGraph";

export default async function RunDetail({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;

  // Placeholder stages — will be fetched from API
  const stages = [
    { agent: "topic_generator", status: "completed" as const },
    { agent: "material_collector", status: "completed" as const },
    { agent: "content_generator", status: "running" as const },
    { agent: "reviewer", status: "pending" as const },
    { agent: "analyst", status: "pending" as const },
  ];

  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-bold mb-4">Run: {runId}</h1>
      <PipelineGraph stages={stages} />
    </main>
  );
}
```

- [ ] **Step 10: Write contents page**

```tsx
// web/src/app/contents/page.tsx
import { ContentCard } from "@/components/ContentCard";

export default function ContentsPage() {
  return (
    <main className="max-w-4xl mx-auto p-6">
      <h1 className="text-xl font-bold mb-4">Content Library</h1>
      <p className="text-sm text-gray-400">Connect API to see content</p>
    </main>
  );
}
```

- [ ] **Step 11: Verify build**

Run: `cd web && npm run build`
Expected: Build succeeds

- [ ] **Step 12: Commit**

```bash
git add web/
git commit -m "feat: add Next.js web UI with dashboard, pipeline graph, and content cards"
```

---

## Phase 5: Integration + Documentation

### Task 21: End-to-end integration test

**Files:**
- Create: `server/tests/integration/test_e2e.py`

- [ ] **Step 1: Write the integration test**

```python
# server/tests/integration/test_e2e.py
"""End-to-end test: run a full pipeline with mock model."""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock

from src.core.config import AppConfig, ModelsConfig, ModelConfig, StorageConfig, ServerConfig
from src.core.engine import Engine
from src.core.state import UserBrief


def _make_mock_model():
    """Create a mock model that returns valid JSON for each agent."""
    model = AsyncMock()
    call_count = 0

    async def generate(prompt: str, **kwargs):
        nonlocal call_count
        call_count += 1

        if "选题" in prompt or "topic" in prompt.lower():
            return json.dumps([
                {"title": "AI编程工具大测评", "angle": "横向对比", "score": 9.0, "reasoning": "热门话题"},
                {"title": "程序员必备AI工具", "angle": "推荐清单", "score": 7.5, "reasoning": "实用向"},
            ])
        elif "素材" in prompt or "material" in prompt.lower():
            return json.dumps([
                {"source": "https://example.com/1", "title": "AI Tools 2026", "snippet": "Review data...", "source_type": "web"},
            ])
        elif "生成" in prompt or "创作" in prompt or "content" in prompt.lower():
            return json.dumps({
                "title": "AI编程工具大测评 🔥 5款工具实测对比",
                "body": "最近一个月，我深度体验了5款主流AI编程工具...\n\n1. Cursor - 最强代码补全\n2. Copilot - GitHub生态整合\n3. Claude Code - 最懂上下文",
                "tags": ["AI", "编程工具", "测评"],
                "image_prompts": ["comparison chart of AI coding tools"],
            })
        elif "审核" in prompt or "review" in prompt.lower():
            return json.dumps({
                "score": 8.5,
                "issues": [],
                "suggestions": ["可以增加具体价格对比"],
            })
        elif "分析" in prompt or "复盘" in prompt or "analy" in prompt.lower():
            return json.dumps({
                "summary": "本次内容质量良好，选题热度高",
                "insights": ["AI工具测评类内容持续受关注", "对比形式读者接受度高"],
                "improvement_suggestions": ["增加价格和性能的量化数据"],
            })
        else:
            return json.dumps({"text": "fallback response"})

    model.generate = generate
    model.generate_image = AsyncMock(return_value=b"fake_image_bytes")
    model.close = AsyncMock()
    return model


@pytest.fixture
def test_config(tmp_path):
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "xiaohongshu_image_text.yaml").write_text("""
name: "小红书图文"
description: "测试管道"
platforms: ["xiaohongshu"]
stages:
  - agent: topic_generator
    config:
      style: "测评"
      count: 3
  - agent: material_collector
    config:
      sources: ["web"]
      max_items: 5
  - agent: content_generator
    config:
      platform: xiaohongshu
      format: image_text
  - agent: reviewer
    config:
      rules: ["platform_compliance", "quality_score"]
      min_score: 7.0
  - agent: analyst
    config:
      metrics: ["engagement"]
""")

    config = AppConfig(
        models=ModelsConfig(
            text=ModelConfig(provider="minimax", api_key="test", base_url="http://test", model="test"),
        ),
        storage=StorageConfig(
            db_path=str(tmp_path / "test.db"),
            assets_dir=str(tmp_path / "assets"),
            outputs_dir=str(tmp_path / "outputs"),
        ),
    )
    return config, pipelines_dir


@pytest.mark.asyncio
async def test_full_pipeline_run(test_config):
    config, pipelines_dir = test_config
    engine = Engine(config, pipelines_dir)

    # Inject mock model
    mock_model = _make_mock_model()
    engine.text_model = mock_model

    await engine.initialize()

    # Override all agents' models with mock
    for agent_name in ["topic_generator", "material_collector", "content_generator", "reviewer", "analyst"]:
        agent = engine.registry.get(agent_name)
        agent.model = mock_model

    brief = UserBrief(topic="AI编程工具测评", keywords=["AI", "coding"], platform_hints=["xiaohongshu"])
    result = await engine.run_pipeline("xiaohongshu_image_text", brief)

    # Verify pipeline completed
    assert result["status"] == "completed"
    assert result["run_id"]

    # Verify all stages produced output
    assert len(result["topics"]) == 2
    assert result["selected_topic"]["title"] == "AI编程工具大测评"
    assert len(result["materials"]) == 1
    assert "xiaohongshu" in result["contents"]
    assert "xiaohongshu" in result["reviews"]
    assert result["reviews"]["xiaohongshu"]["passed"] is True
    assert result["analysis"]["summary"]

    # Verify content was saved to DB
    contents = await engine.state_store.list_contents(run_id=result["run_id"])
    assert len(contents) == 1
    assert contents[0]["platform"] == "xiaohongshu"
    assert contents[0]["status"] == "approved"

    await engine.close()
```

- [ ] **Step 2: Run the integration test**

Run: `cd server && python -m pytest tests/integration/test_e2e.py -v`
Expected: PASS — full pipeline runs with mock model

- [ ] **Step 3: Commit**

```bash
git add server/tests/integration/test_e2e.py
git commit -m "test: add end-to-end integration test with mock model"
```

---

### Task 22: Documentation

**Files:**
- Create: `docs/architecture.md`
- Create: `docs/agent-dev-guide.md`
- Create: `README.md`

- [ ] **Step 1: Write architecture.md**

Concise version of the design spec, focused on "how to understand this codebase":

```markdown
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
```

- [ ] **Step 2: Write agent-dev-guide.md**

```markdown
# How to Write a New Agent

## 1. Create the directory

```
server/src/agents/my_agent/
├── __init__.py
├── agent.py
├── schemas.py
├── prompts/
│   └── my_prompt.j2
└── README.md
```

## 2. Define your config schema

```python
# schemas.py
from pydantic import BaseModel, Field

class MyAgentConfig(BaseModel):
    param1: str = Field(default="value")
    temperature: float = Field(default=0.7)
```

## 3. Implement the agent

```python
# agent.py
from src.agents.base import BaseAgent
from .schemas import MyAgentConfig

class MyAgent(BaseAgent):
    name = "my_agent"
    consumes = ["selected_topic"]    # what I read from State
    produces = ["my_output"]         # what I write to State
    config_schema = MyAgentConfig

    async def run(self, inputs, config):
        topic = inputs["selected_topic"]
        prompt = self.load_prompt("my_prompt.j2", topic=topic)
        response = await self.model.generate(prompt)
        return {"my_output": parse(response)}
```

## 4. Register it

```python
# __init__.py
from .agent import MyAgent
__all__ = ["MyAgent"]
```

Add to `engine.py` `_register_agents()`.

## 5. Add to pipeline YAML

```yaml
stages:
  - agent: my_agent
    config:
      param1: "custom value"
```

## 6. Write tests

```python
# tests/agents/test_my_agent.py
@pytest.mark.asyncio
async def test_my_agent_run(mock_model):
    agent = MyAgent(model=mock_model)
    config = MyAgentConfig()
    result = await agent.run({"selected_topic": {...}}, config)
    assert "my_output" in result
```
```

- [ ] **Step 3: Write README.md**

```markdown
# SuperPipeline

Multi-agent content production pipeline. Automates topic → material → generation → review → analytics.

## Quick Start

```bash
# Install
cd server && pip install -e ".[dev]"

# Configure
cp config.yaml.example config.yaml  # edit API keys

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
```

- [ ] **Step 4: Commit**

```bash
git add docs/architecture.md docs/agent-dev-guide.md README.md
git commit -m "docs: add architecture overview, agent dev guide, and README"
```

---

### Task 23: Run all tests and verify

- [ ] **Step 1: Run full test suite**

Run: `cd server && python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run linter**

Run: `cd server && ruff check src/ tests/`
Expected: No errors (or fix any that appear)

- [ ] **Step 3: Verify CLI works**

Run: `cd server && sp --help`
Expected: Shows help with pipeline, run, status, content subcommands

Run: `cd server && sp pipeline list`
Expected: Shows xiaohongshu_image_text pipeline

- [ ] **Step 4: Verify web build**

Run: `cd web && npm run build`
Expected: Build succeeds

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```
