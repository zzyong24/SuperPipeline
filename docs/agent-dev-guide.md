# How to Write a New Agent

## 1. Create the directory

```
server/src/agents/my_agent/
├── __init__.py
├── agent.py
├── schemas.py
├── prompts/
│   └── my_prompt.j2
└── README.md
```

## 2. Define your config schema

```python
# schemas.py
from pydantic import BaseModel, Field

class MyAgentConfig(BaseModel):
    param1: str = Field(default="value")
    temperature: float = Field(default=0.7)
```

## 3. Implement the agent

```python
# agent.py
from src.agents.base import BaseAgent
from .schemas import MyAgentConfig

class MyAgent(BaseAgent):
    name = "my_agent"
    consumes = ["selected_topic"]    # what I read from State
    produces = ["my_output"]         # what I write to State
    config_schema = MyAgentConfig

    async def run(self, inputs, config):
        topic = inputs["selected_topic"]
        prompt = self.load_prompt("my_prompt.j2", topic=topic)
        response = await self.model.generate(prompt)
        return {"my_output": parse(response)}
```

## 4. Register it

```python
# __init__.py
from .agent import MyAgent
__all__ = ["MyAgent"]
```

Add to `engine.py` `_register_agents()`.

## 5. Add to pipeline YAML

```yaml
stages:
  - agent: my_agent
    config:
      param1: "custom value"
```

## 6. Write tests

```python
# tests/agents/test_my_agent.py
@pytest.mark.asyncio
async def test_my_agent_run(mock_model):
    agent = MyAgent(model=mock_model)
    config = MyAgentConfig()
    result = await agent.run({"selected_topic": {...}}, config)
    assert "my_output" in result
```
