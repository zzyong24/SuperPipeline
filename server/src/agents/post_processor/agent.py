"""Post-Processor Agent — executes skill-based image generation and enriches content."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel

from src.agents.base import BaseAgent
from src.agents.post_processor.schemas import PostProcessorConfig
from src.core.state import ExtractedImage, InlineImageSpec, ImageSource


class PostProcessorAgent(BaseAgent):
    name = "post_processor"
    consumes = ["contents", "extracted_images"]
    produces = ["contents"]
    config_schema = PostProcessorConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: PostProcessorConfig = config
        contents: dict = inputs.get("contents", {})
        extracted_images: list[dict] = inputs.get("extracted_images", [])
        run_id = inputs.get("run_id", "unknown")
        outputs_dir = cfg.output_dir or "outputs"

        all_specs = []
        spec_index_by_platform = {}

        for platform, content_data in contents.items():
            inline_specs = content_data.get("inline_images", [])
            for spec in inline_specs:
                spec_entry = dict(spec)
                spec_entry["_platform"] = platform
                all_specs.append(spec_entry)

        inline_results = await self._execute_inline_images(all_specs, outputs_dir, run_id)

        updated_contents = {}
        for platform, content_data in contents.items():
            platform_image_paths = list(content_data.get("image_paths", []))
            platform_image_sources = list(content_data.get("image_sources", []))
            platform_inline = content_data.get("inline_images", [])

            # Add extracted images (highest priority)
            for img in extracted_images:
                img_path = img.get("image_path", "")
                if img_path and img_path not in platform_image_paths:
                    platform_image_paths.append(img_path)
                    platform_image_sources.append({
                        "image_path": img_path,
                        "source_type": "extracted",
                        "source_detail": img.get("source_doc_path", ""),
                    })

            # Process inline image specs
            for spec in platform_inline:
                spec_dict = dict(spec)
                matching = [r for r in inline_results if r.get("spec") == id(spec)]
                for m in matching:
                    if m.get("output_path"):
                        platform_image_paths.append(m["output_path"])
                        platform_image_sources.append({
                            "image_path": m["output_path"],
                            "source_type": "skill_screenshot",
                            "source_detail": spec.get("skill_name", ""),
                        })

            updated_contents[platform] = dict(content_data)
            updated_contents[platform]["image_paths"] = platform_image_paths
            updated_contents[platform]["image_sources"] = platform_image_sources

        return {
            "contents": updated_contents,
            "inline_images": inline_results,
        }

    async def _execute_inline_images(self, specs: list[dict], output_dir: str, run_id: str) -> list[dict]:
        if not specs:
            return []

        script_path = Path(__file__).parent / "execute_inline_images.py"
        if not script_path.exists():
            return [{"error": f"Script not found: {script_path}", "output_path": "", "spec_index": i} for i in range(len(specs))]

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                str(script_path),
                "--inline-images", json.dumps(specs, ensure_ascii=False),
                "--output-dir", output_dir,
                "--run-id", run_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            if proc.returncode != 0:
                return [{"error": stderr.decode()[:200], "output_path": "", "spec_index": i} for i in range(len(specs))]
            return json.loads(stdout.decode())
        except asyncio.TimeoutError:
            return [{"error": "Timeout after 300s", "output_path": "", "spec_index": i} for i in range(len(specs))]
        except Exception as e:
            return [{"error": str(e), "output_path": "", "spec_index": i} for i in range(len(specs))]
