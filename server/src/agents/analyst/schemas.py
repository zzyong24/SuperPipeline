from pydantic import BaseModel, Field

class AnalystConfig(BaseModel):
    metrics: list[str] = Field(default=["engagement", "reach"])
    temperature: float = Field(default=0.5)
