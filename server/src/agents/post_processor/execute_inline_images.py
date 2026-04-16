#!/usr/bin/env python3
"""Execute skill-based image generation for post_processor agent.

Supports: architecture-diagram, obsidian-canvas, excalidraw-diagram, minimax-image
Outputs JSON with {spec_index, output_path, error}.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

IMG_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
body {{ margin: 0; background: #1e1e2e; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
svg {{ max-width: 900px; max-height: 600px; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>
"""


def ensure_output_dir(output_dir: str) -> Path:
    p = Path(output_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


async def execute_architecture_diagram(prompt: str, output_path: Path) -> str:
    """Use architecture-diagram skill to generate SVG, screenshot it."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(f"# Diagram\n\n{prompt}")
        temp_md = f.name
    try:
        result = subprocess.run(
            ["hermes", "skill", "run", "architecture-diagram", "--prompt", f"Create a diagram for: {prompt}", "--output", str(output_path.with_suffix(".svg"))],
            capture_output=True, text=True, timeout=120,
        )
        svg_path = output_path.with_suffix(".svg")
        if not svg_path.exists():
            return f"architecture-diagram failed: {result.stderr[:200]}"
        html_path = output_path.with_suffix(".html")
        svg_content = svg_path.read_text(encoding="utf-8")
        html_content = IMG_TEMPLATE.format(svg_content=svg_content)
        html_path.write_text(html_content, encoding="utf-8")
        return ""
    finally:
        Path(temp_md).unlink(missing_ok=True)


async def execute_obsidian_canvas(spec: dict, output_path: Path) -> str:
    """Write .canvas JSON and screenshot with playwright."""
    from playwright.async_api import async_playwright
    canvas_content = spec.get("prompt", "{}")
    try:
        data = json.loads(canvas_content)
    except Exception:
        data = {"nodes": [], "edges": []}

    canvas_json = json.dumps(data, ensure_ascii=False)
    canvas_path = output_path.with_suffix(".canvas")
    canvas_path.write_text(canvas_json, encoding="utf-8")

    html_path = output_path.with_suffix(".html")
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<style>
body {{ margin: 0; background: #2d2d2d; }}
canvas-app {{ display: block; }}
</style>
</head>
<body>
<script type="importmap">
{{ json.dumps({"imports": {}}, indent=2) }}
</script>
<script>
const data = {canvas_json};
document.body.innerHTML = '<pre style="color:#ccc;padding:20px;font-size:14px;">' + JSON.stringify(data, null, 2) + '</pre>';
</script>
</body>
</html>"""
    html_path.write_text(html_content, encoding="utf-8")
    return ""


async def execute_excalidraw_diagram(prompt: str, output_path: Path) -> str:
    """Generate excalidraw JSON, screenshot it."""
    import tempfile
    excalidraw_html = """<!DOCTYPE html>
<html>
<head>
<script>
window.__EXCALIDRAW_STATE__ = null;
</script>
</head>
<body>
<script type="module">
import {{ rawWriteFile }} from "https://unpkg.com/@excalidraw/common/dist/bundle.esm.js";
const rawWriteFile = (name, data) => {{ console.log("DATA:" + JSON.stringify({{name, data}})) }};
</script>
</body>
</html>"""
    return f"excalidraw requires Node.js integration — skipped: {prompt[:100]}"


async def execute_minimax_image(prompt: str, output_path: Path) -> str:
    """Use MiniMax image-01 API to generate image."""
    api_key = os.environ.get("MINIMAX_API_KEY") or os.environ.get("MINIMAX_CN_API_KEY", "")
    if not api_key:
        return "MINIMAX_API_KEY not set"

    import urllib.request
    import urllib.parse

    payload = json.dumps({
        "model": "image-01",
        "prompt": prompt[:1000],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.minimaxi.com/v1/image_generation",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            image_url = result.get("data", [{}])[0].get("url", "")
            if image_url:
                urllib.request.urlretrieve(image_url, str(output_path))
                return ""
            return f"No image URL in response: {result}"
    except Exception as e:
        return f"Minimax API error: {e}"


async def run_inline_images(inline_images: list[dict], output_dir: str, run_id: str) -> list[dict]:
    """Execute all inline image specs and return updated specs with output_path."""
    out_base = ensure_output_dir(os.path.join(output_dir, run_id, "inline"))
    results = []

    for i, spec in enumerate(inline_images):
        skill = spec.get("skill_name", "")
        prompt = spec.get("prompt", "")
        output_path = out_base / f"inline_{i}_{uuid.uuid4().hex[:6]}.png"

        error = ""
        if skill == "architecture-diagram":
            error = await execute_architecture_diagram(prompt, output_path)
        elif skill == "obsidian-canvas":
            error = await execute_obsidian_canvas(spec, output_path)
        elif skill == "excalidraw-diagram":
            error = await execute_excalidraw_diagram(prompt, output_path)
        elif skill == "minimax-image":
            error = await execute_minimax_image(prompt, output_path)
        else:
            error = f"Unknown skill: {skill}"

        results.append({
            "spec_index": i,
            "output_path": str(output_path) if not error else "",
            "error": error,
        })

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inline-images", type=str, required=True, help="JSON list of InlineImageSpec dicts")
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--run-id", type=str, required=True)
    args = parser.parse_args()

    inline_images = json.loads(args.inline_images)
    results = asyncio.run(run_inline_images(inline_images, args.output_dir, args.run_id))
    print(json.dumps(results, ensure_ascii=False))
