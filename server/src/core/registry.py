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
