"""High-level engine facade — wires together all components."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from src.core.config import AppConfig
from src.core.models import create_model_adapter, ModelAdapter
from src.core.orchestrator import Orchestrator
from src.core.pipeline_loader import load_pipeline
from src.core.registry import AgentRegistry
from src.core.state import PipelineConfig, UserBrief
from src.storage.state_store import StateStore
from src.storage.asset_store import AssetStore


class Engine:
    def __init__(self, config: AppConfig, pipelines_dir: Path) -> None:
        self.config = config
        self.pipelines_dir = pipelines_dir
        self.text_model: ModelAdapter = create_model_adapter(config.models.text)
        self.registry = AgentRegistry()
        self.state_store = StateStore(config.storage.database_url)
        self.orchestrator = Orchestrator(self.registry, state_store=self.state_store)
        self.asset_store = AssetStore(config.storage.assets_dir, config.storage.outputs_dir)

    async def initialize(self) -> None:
        await self.state_store.initialize()
        self._register_agents()

    def _register_agents(self) -> None:
        from src.agents.topic_generator import TopicGeneratorAgent
        from src.agents.material_collector import MaterialCollectorAgent
        from src.agents.content_generator import ContentGeneratorAgent
        from src.agents.reviewer import ReviewerAgent
        from src.agents.analyst import AnalystAgent
        from src.agents.document_synthesizer import DocumentSynthesizerAgent
        from src.agents.image_extractor import ImageExtractorAgent
        from src.agents.post_processor import PostProcessorAgent

        for agent_cls in [
            TopicGeneratorAgent, MaterialCollectorAgent, ContentGeneratorAgent,
            ReviewerAgent, AnalystAgent, DocumentSynthesizerAgent,
            ImageExtractorAgent, PostProcessorAgent,
        ]:
            self.registry.register(agent_cls, model=self.text_model)

    def load_pipeline(self, name: str) -> PipelineConfig:
        yaml_file = self.pipelines_dir / f"{name}.yaml"
        return load_pipeline(yaml_file)

    async def run_pipeline(self, pipeline_name: str, brief: UserBrief) -> dict:
        pipeline_config = self.load_pipeline(pipeline_name)
        run_id = uuid.uuid4().hex[:12]
        await self.state_store.save_run(run_id, pipeline_name, "running", {})

        try:
            result = await self.orchestrator.run(pipeline_config, brief, run_id=run_id)

            for platform, content_data in result.get("contents", {}).items():
                content_id = f"{run_id}-{platform}"
                review = result.get("reviews", {}).get(platform, {})
                status = "approved" if review.get("passed", False) else "pending_review"
                await self.state_store.save_content(
                    content_id=content_id, run_id=run_id, platform=platform,
                    title=content_data.get("title", ""), body=content_data.get("body", ""),
                    status=status, tags=content_data.get("tags", []),
                    image_paths=content_data.get("image_paths", []),
                )

            await self.state_store.update_run(run_id, status=result.get("stage", "completed"), state=result)
            return {"run_id": run_id, "status": result.get("stage", "completed"), **result}

        except Exception as e:
            await self.state_store.update_run(run_id, status="failed", state={"error": str(e)})
            return {"run_id": run_id, "status": "failed", "error": str(e)}

    async def rerun_from_stage(
        self,
        run_id: str,
        from_agent: str,
        config_overrides: dict | None = None,
        model_override: str | None = None,
        prompt_override: str | None = None,
        only: bool = False,
    ) -> dict:
        """Rerun a pipeline from a specific stage, optionally cascading to all subsequent stages.

        Args:
            run_id: The run to modify
            from_agent: The agent/stage name to start rerunning from
            config_overrides: Override config params for the from_agent stage
            model_override: Override model name for the from_agent stage
            prompt_override: Override prompt for the from_agent stage
            only: If True, only rerun this one stage. If False (default), cascade to all subsequent stages.

        Returns:
            Updated pipeline state dict
        """
        # 1. Load the run from DB
        run = await self.state_store.get_run(run_id)
        if run is None:
            raise ValueError(f"Run '{run_id}' not found")

        state = run.get("state", {})
        pipeline_name = run.get("pipeline_name", "")

        # 2. Find the pipeline config
        # pipeline_name in DB is the file stem passed to run_pipeline()
        try:
            pipeline_config = self.load_pipeline(pipeline_name)
        except FileNotFoundError:
            # Fallback: search by display name in case pipeline_name is the YAML name field
            from src.core.pipeline_loader import list_pipelines
            pipeline_config = None
            for p in list_pipelines(self.pipelines_dir):
                yaml_file = self.pipelines_dir / p["file"]
                pc = load_pipeline(yaml_file)
                if pc.name == pipeline_name:
                    pipeline_config = pc
                    break
            if pipeline_config is None:
                raise ValueError(f"Pipeline config for '{pipeline_name}' not found")

        # 3. Find the from_agent's position in the stage list
        stage_names = [s.agent for s in pipeline_config.stages]
        if from_agent not in stage_names:
            raise ValueError(f"Agent '{from_agent}' not found in pipeline stages: {stage_names}")

        from_idx = stage_names.index(from_agent)

        # 4. Determine which stages to rerun
        if only:
            stages_to_run = [pipeline_config.stages[from_idx]]
        else:
            stages_to_run = pipeline_config.stages[from_idx:]

        # 5. Get the snapshot for from_agent to read its inputs
        snapshot = await self.state_store.get_snapshot(run_id, from_agent)
        if snapshot is None:
            raise ValueError(f"No snapshot found for agent '{from_agent}' in run '{run_id}'")

        # 6. Build working state from current run state
        working_state = dict(state)

        # 7. Rerun each stage
        for i, stage in enumerate(stages_to_run):
            agent = self.registry.get(stage.agent)

            # Build effective stage config — overrides only apply to the first (from_agent) stage
            effective_config = dict(stage.config)
            if i == 0 and config_overrides:
                effective_config.update(config_overrides)

            effective_stage = stage.model_copy(update={
                "config": effective_config,
                **({"model_override": model_override} if i == 0 and model_override else {}),
                **({"prompt_override": prompt_override} if i == 0 and prompt_override else {}),
            })

            # Validate config
            config = agent.config_schema.model_validate(effective_stage.config)
            if effective_stage.prompt_override:
                object.__setattr__(config, '_prompt_override', effective_stage.prompt_override)

            # Extract inputs from working state
            inputs = {key: working_state[key] for key in agent.consumes if key in working_state}

            # Get next version
            version = await self.state_store.get_next_version(run_id, stage.agent)

            # Build snapshot config
            snapshot_config = {
                "agent_config": effective_config,
                "model_override": effective_stage.model_override,
                "prompt_override": effective_stage.prompt_override,
                "on_error": stage.on_error,
                "retry_count": stage.retry_count,
            }

            # Execute
            start_time = time.monotonic()
            try:
                outputs = await agent.run(inputs, config)
                elapsed = int((time.monotonic() - start_time) * 1000)

                # Save snapshot
                await self.state_store.save_snapshot(
                    run_id=run_id, agent=stage.agent, version=version,
                    status="completed", config=snapshot_config, inputs=inputs,
                    outputs=outputs, error=None, duration_ms=elapsed,
                )

                # Merge outputs into working state
                for key, value in outputs.items():
                    if isinstance(value, dict) and isinstance(working_state.get(key), dict):
                        merged = dict(working_state[key])
                        merged.update(value)
                        working_state[key] = merged
                    else:
                        working_state[key] = value

            except Exception as e:
                elapsed = int((time.monotonic() - start_time) * 1000)
                await self.state_store.save_snapshot(
                    run_id=run_id, agent=stage.agent, version=version,
                    status="failed", config=snapshot_config, inputs=inputs,
                    outputs=None, error=str(e), duration_ms=elapsed,
                )
                working_state["stage"] = "failed"
                errors = list(working_state.get("errors", []))
                errors.append({
                    "agent": stage.agent,
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "recoverable": False,
                })
                working_state["errors"] = errors
                break

        # 8. Update the run state in DB
        final_status = working_state.get("stage", "completed")
        if final_status != "failed":
            working_state["stage"] = "completed"
            final_status = "completed"

        await self.state_store.update_run(run_id, status=final_status, state=working_state)

        # 9. Re-save contents to DB (if content_generator was rerun)
        if "contents" in working_state:
            for platform, content_data in working_state.get("contents", {}).items():
                content_id = f"{run_id}-{platform}"
                review = working_state.get("reviews", {}).get(platform, {})
                status = "approved" if review.get("passed", False) else "pending_review"
                existing = await self.state_store.get_content(content_id)
                if existing:
                    await self.state_store.update_content(
                        content_id, title=content_data.get("title", ""),
                        body=content_data.get("body", ""),
                        status=status,
                        tags=content_data.get("tags", []),
                    )
                else:
                    await self.state_store.save_content(
                        content_id=content_id, run_id=run_id, platform=platform,
                        title=content_data.get("title", ""), body=content_data.get("body", ""),
                        status=status, tags=content_data.get("tags", []),
                        image_paths=content_data.get("image_paths", []),
                    )

        return working_state

    async def close(self) -> None:
        await self.state_store.close()
        await self.text_model.close()
