#!/usr/bin/env python3
"""Run douyin pipeline with Hermes deployment article as source document."""

import asyncio
import json
import uuid
from pathlib import Path

from src.core.config import load_config
from src.core.engine import Engine
from src.core.state import UserBrief, SourceDocument


async def main():
    config = load_config(Path("config.yaml"))
    pipelines_dir = Path("pipelines")
    engine = Engine(config, pipelines_dir)
    await engine.initialize()

    # Read source article
    article_path = "/Users/zyongzhu/ThirdSpace/space/found/study/ai/20260416_Hermes_Agent_调研.md"
    article_content = Path(article_path).read_text(encoding="utf-8")

    # Strip frontmatter
    lines = article_content.split("\n")
    if lines[0].strip() == "---":
        end = lines[1:].index("---")
        body = "\n".join(lines[end + 2:])
    else:
        body = article_content

    doc = SourceDocument(
        file_path=article_path,
        title="Hermes Agent 调研报告",
        content=body.strip(),
    )

    brief = UserBrief(
        topic="Hermes Agent 云服务器 Docker 部署教程",
        keywords=["Hermes Agent", "云服务器", "Docker", "部署", "安装"],
        platform_hints=["douyin"],
        style="种草教程风格，实操性强，面向想自建 AI 助手的用户",
        source_documents=[doc],
    )

    print(f"Topic: {brief.topic}")
    print(f"Source documents: {len(brief.source_documents)}")
    print(f"Document content length: {len(doc.content)} chars")
    print("Starting pipeline run...")

    run_id = uuid.uuid4().hex[:12]
    try:
        result = await engine.run_pipeline("douyin_image_text", brief)
        print(f"\nPipeline completed!")
        print(f"Run ID: {run_id}")
        print(f"Final stage: {result.get('stage')}")
        print(f"Errors: {result.get('errors', [])}")

        materials = result.get("materials", [])
        print(f"\nMaterials count: {len(materials)}")
        if materials:
            for i, m in enumerate(materials[:3]):
                print(f"  Material {i}: source={m.get('source','')[:60]}, snippet_len={len(m.get('snippet',''))}")

        doc_synth = result.get("document_synthesizer_output", {})
        print(f"\ndocument_synthesizer_output keys: {list(doc_synth.keys()) if doc_synth else 'empty'}")
        if doc_synth:
            print(f"  summary len: {len(doc_synth.get('summary', ''))}")
            print(f"  knowledge_points: {len(doc_synth.get('knowledge_points', []))}")
        print(f"extracted_images: {len(result.get('extracted_images', []))}")

        reviews = result.get("reviews", {})
        print(f"\nReviews: {json.dumps(reviews, indent=2, ensure_ascii=False) if reviews else 'empty'}")
        print(f"Review iteration: {result.get('review_iteration', 'not in result')}")
        print(f"Previous review issues: {result.get('previous_review_issues', [])}")

        contents = result.get("contents", {})
        for platform, content in contents.items():
            print(f"\n=== {platform} ===")
            print(f"Title: {content.get('title', '(no title)')}")
            print(f"Body length: {len(content.get('body', ''))} chars")
            print(f"Tags: {content.get('tags', [])}")
            print(f"Image paths: {content.get('image_paths', [])}")
            print(f"Body preview:\n{content.get('body', '')[:800]}...")

    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
