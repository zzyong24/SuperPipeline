from pydantic import BaseModel, Field

class MaterialCollectConfig(BaseModel):
    sources: list[str] = Field(default=["web"])
    max_items: int = Field(default=10)
    temperature: float = Field(default=0.3)
