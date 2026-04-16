"""Image Extractor Agent — extracts images from source documents and generates captions."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.image_extractor.schemas import ImageExtractorConfig
from src.core.state import SourceDocument, ExtractedImage
from src.core.models import ModelAdapter


class ImageExtractorAgent(BaseAgent):
    name = "image_extractor"
    consumes = ["source_documents"]
    produces = ["extracted_images"]
    config_schema = ImageExtractorConfig

    def __init__(self, model: ModelAdapter | None = None, vision_model: ModelAdapter | None = None) -> None:
        super().__init__(model)
        self.vision_model = vision_model

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: ImageExtractorConfig = config
        docs = [SourceDocument.model_validate(d) for d in inputs.get("source_documents", [])]

        if not docs:
            return {"extracted_images": []}

        all_images: list[ExtractedImage] = []

        for doc in docs:
            doc_path = Path(doc.file_path)
            if not doc_path.exists():
                continue

            # Find images in the same directory as the document and in assets subdirs
            base_dir = doc_path.parent if doc_path.is_file() else doc_path
            search_dirs = [base_dir]
            assets_dir = base_dir / "assets" / "images"
            if assets_dir.exists():
                search_dirs.append(assets_dir)
            # Also look for images at the same level as the .md (common in some article structures)
            for sibling_dir in base_dir.iterdir():
                if sibling_dir.is_dir() and sibling_dir.name in ("images", "assets", "img", "figures"):
                    search_dirs.append(sibling_dir)

            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"}
            found_images = []
            for search_dir in search_dirs:
                for ext in image_extensions:
                    found_images.extend(search_dir.glob(f"*{ext}"))
                    found_images.extend(search_dir.glob(f"*{ext.upper()}"))
                    found_images.extend(search_dir.glob(f"*/*.{ext}"))  # one level deep

            for img_path in found_images[: cfg.max_images]:
                caption = await self._generate_caption(img_path)
                all_images.append(
                    ExtractedImage(
                        image_path=str(img_path.resolve()),
                        source_doc_path=doc.file_path,
                        caption=caption,
                        page_anchor="",
                    )
                )

        return {"extracted_images": [img.model_dump() for img in all_images]}

    async def _generate_caption(self, image_path: Path) -> str:
        if self.vision_model is None:
            return ""
        try:
            prompt = f"描述这张图片的内容，用于文章配图。简短50字以内。"
            result = await self.vision_model.generate_image_caption(str(image_path), prompt)
            return result
        except Exception:
            return ""
