"""Orchestrator — dynamically builds LangGraph pipelines from YAML config."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.base import BaseAgent
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, PipelineState, StageConfig, UserBrief


class Orchestrator:
    """Reads pipeline config, assembles a LangGraph StateGraph, and runs it."""

    def __init__(self, registry: AgentRegistry, state_store=None) -> None:
        self.registry = registry
        self.state_store = state_store
        self.checkpointer = MemorySaver()

    def _wrap_agent(self, agent: BaseAgent, stage_config: StageConfig, run_id: str | None = None):
        """Wrap an agent into a LangGraph node function with retry, on_error, and snapshot support."""
        config = agent.config_schema.model_validate(stage_config.config)
        on_error = stage_config.on_error
        retry_count = stage_config.retry_count

        # Build snapshot config once (immutable per node)
        snapshot_config = {
            "agent_config": stage_config.config,
            "model_override": stage_config.model_override,
            "prompt_override": stage_config.prompt_override,
            "on_error": stage_config.on_error,
            "retry_count": stage_config.retry_count,
        }

        async def _save_snapshot(inputs, outputs, status, error, duration_ms):
            """Best-effort snapshot save — never crashes the pipeline."""
            if not self.state_store or not run_id:
                return
            try:
                version = await self.state_store.get_next_version(run_id, agent.name)
                await self.state_store.save_snapshot(
                    run_id=run_id, agent=agent.name, version=version,
                    status=status, config=snapshot_config, inputs=inputs,
                    outputs=outputs, error=error, duration_ms=duration_ms,
                )
            except Exception:
                pass

        async def node_fn(state: PipelineState) -> dict:
            updates: dict[str, Any] = {"stage": agent.name}

            # Extract inputs for snapshot
            inputs = {key: state[key] for key in agent.consumes if key in state}

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

                await _save_snapshot(
                    inputs, None, "failed",
                    f"Missing required inputs: {agent.consumes}", 0,
                )

                if on_error == "skip":
                    return updates
                updates["stage"] = "failed"
                return updates

            start_time = time.monotonic()
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

                    elapsed = int((time.monotonic() - start_time) * 1000)
                    await _save_snapshot(inputs, outputs, "completed", None, elapsed)
                    return updates
                except Exception as e:
                    last_exception = e
                    if attempt < retry_count - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))

            elapsed = int((time.monotonic() - start_time) * 1000)
            await _save_snapshot(
                inputs, None, "failed", str(last_exception), elapsed,
            )

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

    def build_graph(self, pipeline_config: PipelineConfig, stage_overrides: dict[str, dict] | None = None, run_id: str | None = None) -> StateGraph:
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
            graph.add_node(stage.agent, self._wrap_agent(agent, effective_stage, run_id=run_id))

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
        graph = self.build_graph(pipeline_config, stage_overrides=stage_overrides, run_id=run_id)
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
