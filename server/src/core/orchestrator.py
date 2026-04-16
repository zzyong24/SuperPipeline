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
        if stage_config.prompt_override:
            object.__setattr__(config, '_prompt_override', stage_config.prompt_override)
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

            # Debug: print inputs for key agents
            if agent.name in ("reviewer", "content_generator", "post_processor"):
                print(f"[DEBUG node_fn {agent.name}] inputs keys={list(state.keys())}", flush=True)
                if agent.name == "reviewer":
                    print(f"[DEBUG reviewer] previous_issues={state.get('previous_review_issues', [])}, review_iteration={state.get('review_iteration', 'missing')}", flush=True)

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
        """Build a LangGraph StateGraph from pipeline config.

        Supports review loop: if reviewer finds hard-issues (issues starting with ❌),
        routes back to content_generator for correction before proceeding to analyst.
        """
        graph = StateGraph(PipelineState)

        stages = pipeline_config.stages
        if not stages:
            raise ValueError("Pipeline has no stages")

        # Find reviewer and content_generator positions for loop routing
        reviewer_idx = None
        content_generator_idx = None
        for i, stage in enumerate(stages):
            if stage.agent == "reviewer":
                reviewer_idx = i
            if stage.agent == "content_generator":
                content_generator_idx = i

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

            # Special routing: reviewer goes back to content_generator on failure
            if current == "reviewer" and content_generator_idx is not None:
                reviewer_agent_name = "reviewer"
                cg_agent_name = "content_generator"

                def _reviewer_route(state, _cg=cg_agent_name, _next=next_stage, _max=3):
                    """Route reviewer output: if review failed, back to content_generator; else continue.
                    Review fails if: score < min_score OR hard issues (❌) exist.
                    Max 3 review iterations to prevent infinite loops.
                    """
                    iteration = state.get("review_iteration", 0)
                    reviews = state.get("reviews", {})
                    hard_issues_found = []
                    review_failed = False
                    for platform, review in reviews.items():
                        issues = review.get("issues", [])
                        score = review.get("score", 10)
                        passed = review.get("passed", False)
                        # Check for ❌ hard issues
                        hard_issues = [issue for issue in issues if issue.startswith("❌")]
                        if hard_issues:
                            hard_issues_found.extend(hard_issues)
                        # Review also fails if passed=False (below min_score)
                        if not passed:
                            review_failed = True

                    print(f"[DEBUG _reviewer_route] iteration={iteration}, hard_issues={hard_issues_found}, review_failed={review_failed}, max={_max}", flush=True)
                    if iteration >= _max:
                        print(f"[DEBUG _reviewer_route] Max iterations reached ({_max}), proceeding to analyst", flush=True)
                        return _next

                    if hard_issues_found or review_failed:
                        print(f"[DEBUG _reviewer_route] Issues found or review failed, routing back to content_generator", flush=True)
                        return _cg
                    print(f"[DEBUG _reviewer_route] Review passed, proceeding to analyst", flush=True)
                    return _next

                graph.add_conditional_edges(
                    reviewer_agent_name,
                    _reviewer_route,
                    {cg_agent_name: cg_agent_name, next_stage: next_stage},
                )
            else:
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
            "selected_topic": {},
            "source_documents": user_brief.model_dump().get("source_documents", []),
            "document_synthesizer_output": {},
            "extracted_images": [],
            "materials": [],
            "contents": {},
            "review_iteration": 0,
            "previous_review_issues": [],
            "inline_images": [],
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
