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
        on_error = stage_config.on_error
        retry_count = stage_config.retry_count

        async def node_fn(state: PipelineState) -> dict:
            updates: dict[str, Any] = {"stage": agent.name}

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
                    return updates
                updates["stage"] = "failed"
                return updates

            inputs = {key: state[key] for key in agent.consumes if key in state}

            last_exception = None
            for attempt in range(max(1, retry_count)):
                try:
                    outputs = await agent.run(inputs, config)
                    if not agent.validate_outputs(outputs):
                        raise ValueError(f"Agent did not produce required outputs: {agent.produces}")
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
                        await asyncio.sleep(1.0 * (attempt + 1))

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
                return updates
            else:
                updates["stage"] = "failed"

            return updates

        return node_fn

    def build_graph(self, pipeline_config: PipelineConfig, stage_overrides: dict[str, dict] | None = None) -> StateGraph:
        """Build a LangGraph StateGraph from pipeline config."""
        graph = StateGraph(PipelineState)

        stages = pipeline_config.stages
        if not stages:
            raise ValueError("Pipeline has no stages")

        for stage in stages:
            effective_stage = stage
            if stage_overrides and stage.agent in stage_overrides:
                merged_config = {**stage.config, **stage_overrides[stage.agent]}
                effective_stage = stage.model_copy(update={"config": merged_config})
            agent = self.registry.get(stage.agent)
            graph.add_node(stage.agent, self._wrap_agent(agent, effective_stage))

        graph.add_edge(START, stages[0].agent)
        for i in range(len(stages) - 1):
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
        stage_overrides: dict[str, dict] | None = None,
    ) -> dict:
        """Build and execute a pipeline."""
        run_id = run_id or uuid.uuid4().hex[:12]
        graph = self.build_graph(pipeline_config, stage_overrides=stage_overrides)
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

        if result.get("stage") != "failed":
            result["stage"] = "completed"

        return result
