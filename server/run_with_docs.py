#!/usr/bin/env python3
"""Run douyin pipeline with a source document as input."""

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import load_config
from src.core.engine import Engine
from src.core.state import UserBrief, SourceDocument


async def main():
    # Load config
    config = load_config(Path("config.yaml"))
    pipelines_dir = Path("pipelines")

    engine = Engine(config, pipelines_dir)
    await engine.initialize()

    # Read the source article
    article_path = "/Users/zyongzhu/ThirdSpace/flux/intake/articles_20260416_011852_Hermes_Agent_Self-Evolution_System__A_Detailed_Sim.md"
    article_content = Path(article_path).read_text(encoding="utf-8")

    # Strip frontmatter
    lines = article_content.split("\n")
    if lines[0].strip() == "---":
        end = lines[1:].index("---")
        body = "\n".join(lines[end + 2 :])
    else:
        body = article_content

    # Build source document
    doc = SourceDocument(
        file_path=article_path,
        title="Hermes Agent Self-Evolution System: A Detailed Similarity Analysis with Evolver",
        content=body.strip(),
    )

    # Build brief with source_documents
    brief = UserBrief(
        topic="Hermes Agent 与 Evolver 架构相似度分析",
        keywords=["Hermes Agent", "Evolver", "self-evolution", "EvoMap", "plagiarism"],
        platform_hints=["douyin"],
        style="信息转述，客观中立，不表达观点",
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

        # Debug: print material count
        materials = result.get("materials", [])
        print(f"\nMaterials count: {len(materials)}")
        if materials:
            for i, m in enumerate(materials[:3]):
                print(f"  Material {i}: source={m.get('source','')[:60]}, snippet_len={len(m.get('snippet',''))}")

        # Debug: print document_synthesizer_output
        doc_synth = result.get("document_synthesizer_output", {})
        print(f"\ndocument_synthesizer_output keys: {list(doc_synth.keys()) if doc_synth else 'empty'}")
        if doc_synth:
            print(f"  summary len: {len(doc_synth.get('summary', ''))}")
            print(f"  knowledge_points: {len(doc_synth.get('knowledge_points', []))}")
        print(f"extracted_images: {len(result.get('extracted_images', []))}")

        # Print reviews
        reviews = result.get("reviews", {})
        print(f"\nReviews: {json.dumps(reviews, indent=2, ensure_ascii=False) if reviews else 'empty'}")

        # Print review iteration info
        print(f"\nReview iteration: {result.get('review_iteration', 'not in result')}")
        print(f"Previous review issues: {result.get('previous_review_issues', [])}")
        contents = result.get("contents", {})
        for platform, content in contents.items():
            print(f"\n=== {platform} ===")
            print(f"Title: {content.get('title', '(no title)')}")
            print(f"Body length: {len(content.get('body', ''))} chars")
            print(f"Tags: {content.get('tags', [])}")
            print(f"Image paths: {content.get('image_paths', [])}")
            print(f"Image sources: {content.get('image_sources', [])}")
            print(f"Inline images: {content.get('inline_images', [])}")
            print(f"\nBody preview:\n{content.get('body', '')[:500]}...")

    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
