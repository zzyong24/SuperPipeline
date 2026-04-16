"""Trace all LLM prompts for a pipeline run."""
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import load_config
from core.engine import Engine
from core.models import MiniMaxAdapter
from core.state import UserBrief

TRACE = []

_original_generate = MiniMaxAdapter.generate

async def traced_generate(self, prompt: str, **kwargs):
    messages = kwargs.get("messages", [{"role": "user", "content": prompt}])

    # Reconstruct full prompt from messages (last user message is the main prompt)
    trace_entry = {
        "model": self.config.model,
        "base_url": self.config.base_url,
        "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        "temperature": kwargs.get("temperature", self.config.temperature if hasattr(self.config, 'temperature') else None),
        "messages": messages,
        "prompt_text": prompt,  # raw prompt if no messages
    }
    TRACE.append(trace_entry)

    return await _original_generate(self, prompt, **kwargs)

MiniMaxAdapter.generate = traced_generate


async def main():
    pipeline_name = "x_tweet"
    topic = "Hermes Agent 的周期性反思机制"

    config_path = Path(os.environ.get("SP_CONFIG", Path(__file__).parent / "config.yaml"))
    pipelines_dir = Path(os.environ.get("SP_PIPELINES_DIR", Path(__file__).parent / "pipelines"))

    config = load_config(config_path)
    engine = Engine(config, pipelines_dir)

    await engine.initialize()
    brief = UserBrief(topic=topic)
    result = await engine.run_pipeline(pipeline_name, brief)
    await engine.close()

    # Output
    print(f"\n{'='*60}")
    print(f"TRACE RESULTS — Pipeline: {pipeline_name} | Topic: {topic}")
    print(f"{'='*60}\n")

    for i, entry in enumerate(TRACE, 1):
        print(f"\n{'─'*60}")
        print(f"[{i}] Model: {entry['model']}")
        print(f"    Temperature: {entry['temperature']}")
        print(f"    Max tokens: {entry['max_tokens']}")
        print(f"    Base URL: {entry['base_url']}")
        print(f"    Messages count: {len(entry['messages'])}")

        for j, msg in enumerate(entry['messages']):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if isinstance(content, list):
                # blocks format
                text_parts = []
                for block in content:
                    if block.get('type') == 'text':
                        text_parts.append(block['text'])
                    elif block.get('type') == 'thinking':
                        text_parts.append(f"[thinking: {block.get('thinking','')[:100]}...]")
                content = '\n'.join(text_parts)
            print(f"    Message[{j}] role={role}:")
            for line in content.split('\n'):
                print(f"      {line}")

        print()

    # Final result
    print(f"\n{'='*60}")
    print("FINAL RESULT")
    print(f"{'='*60}")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return result


if __name__ == "__main__":
    asyncio.run(main())
