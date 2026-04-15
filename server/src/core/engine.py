"""High-level engine facade — wires together all components."""

from __future__ import annotations

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
        self.orchestrator = Orchestrator(self.registry)
        self.state_store = StateStore(config.storage.db_path)
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

        for agent_cls in [TopicGeneratorAgent, MaterialCollectorAgent, ContentGeneratorAgent, ReviewerAgent, AnalystAgent]:
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

    async def close(self) -> None:
        await self.state_store.close()
        await self.text_model.close()
