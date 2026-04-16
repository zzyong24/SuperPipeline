"""Reconstruct actual LLM prompts from snapshots using Jinja2 templates."""
import asyncio
import json
import sys
from pathlib import Path

import jinja2

sys.path.insert(0, str(Path(__file__).parent / "src"))

from storage.state_store import StateStore
from agents.topic_generator.schemas import TopicGenConfig
from agents.material_collector.schemas import MaterialCollectConfig
from agents.content_generator.schemas import ContentGenConfig
from agents.reviewer.schemas import ReviewerConfig
from agents.analyst.schemas import AnalystConfig
from agents.base import extract_json

# ── Jinja2 env helpers ──────────────────────────────────────────────

def make_env(agent_name):
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(Path(__file__).parent / "src" / "agents" / agent_name / "prompts")),
        undefined=jinja2.StrictUndefined,
    )

def render(agent_name, template_name, **kwargs):
    env = make_env(agent_name)
    tmpl = env.get_template(template_name)
    return tmpl.render(**kwargs)

# ── Platform rules ────────────────────────────────────────────────────

X_RULES = (
    "平台：X (Twitter)。要求：\n"
    "- 每条推文不超过 280 字符\n"
    "- 简洁有力，观点鲜明\n"
    "- 最多 5 个话题标签\n"
    "- 最多 4 张配图\n"
    "- 用提问或犀利观点引发互动"
)

# ── Reconstruct each node's prompt ────────────────────────────────────

async def main():
    store = StateStore("data/superpipeline.db")
    await store.initialize()
    snapshots = await store.list_snapshots("7f4cdd76461e")
    await store.close()

    # Build dict: agent → snapshot
    snap_by_agent = {s["agent"]: s for s in snapshots}

    print("=" * 70)
    print("NODE 1 — topic_generator")
    print("=" * 70)
    s = snap_by_agent["topic_generator"]
    cfg = TopicGenConfig(style="观点输出", count=5)
    prompt = render(
        "topic_generator", "generate.j2",
        topic="Hermes Agent 的周期性反思机制",
        keywords=[],
        style="观点输出",
        platform_hints=[],
        count=5,
    )
    print(prompt)
    print()

    print("=" * 70)
    print("NODE 2 — material_collector")
    print("=" * 70)
    s = snap_by_agent["material_collector"]
    topic_in = s["inputs"]["selected_topic"]
    cfg = MaterialCollectConfig(sources=["web"], max_items=5)
    prompt = render(
        "material_collector", "collect.j2",
        title=topic_in["title"],
        angle=topic_in["angle"],
        max_items=5,
    )
    print(prompt)
    print()

    print("=" * 70)
    print("NODE 3 — content_generator")
    print("=" * 70)
    s = snap_by_agent["content_generator"]
    topic_in = s["inputs"]["selected_topic"]
    mats_in = s["inputs"]["materials"]
    cfg = ContentGenConfig(platform="x", format="tweet")
    prompt = render(
        "content_generator", "generate.j2",
        platform="x",
        format="tweet",
        topic_title=topic_in["title"],
        topic_angle=topic_in["angle"],
        materials=mats_in,
        platform_rules=X_RULES,
        style="",
    )
    print(prompt)
    print()

    print("=" * 70)
    print("NODE 4 — reviewer")
    print("=" * 70)
    s = snap_by_agent["reviewer"]
    contents_in = s["inputs"]["contents"]
    x_content = contents_in["x"]
    cfg = ReviewerConfig(rules=["platform_compliance", "quality_score"], min_score=7.0)
    prompt = render(
        "reviewer", "review.j2",
        platform="x",
        title=x_content["title"],
        body=x_content["body"],
        tags=x_content["tags"],
        platform_rules=X_RULES,
        rules=["platform_compliance", "quality_score"],
    )
    print(prompt)
    print()

    print("=" * 70)
    print("NODE 5 — analyst")
    print("=" * 70)
    s = snap_by_agent["analyst"]
    cfg = AnalystConfig(metrics=["engagement", "reach"])
    prompt = render(
        "analyst", "analyze.j2",
        contents=contents_in,
        reviews=s["inputs"]["reviews"],
        metrics=["engagement", "reach"],
    )
    print(prompt)


if __name__ == "__main__":
    asyncio.run(main())
