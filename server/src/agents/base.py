"""Base class for all pipeline agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar

import jinja2
from pydantic import BaseModel

from src.core.models import ModelAdapter


class BaseAgent(ABC):
    """Standard interface every Agent must implement."""

    name: ClassVar[str]
    consumes: ClassVar[list[str]]
    produces: ClassVar[list[str]]
    config_schema: ClassVar[type[BaseModel]]

    def __init__(self, model: ModelAdapter | None = None) -> None:
        self.model = model
        self._jinja_env: jinja2.Environment | None = None

    @abstractmethod
    async def run(self, inputs: dict, config: BaseModel) -> dict:
        """Execute this agent's logic."""

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
