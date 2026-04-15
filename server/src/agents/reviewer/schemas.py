from pydantic import BaseModel, Field

class ReviewerConfig(BaseModel):
    rules: list[str] = Field(default=["quality_score"])
    min_score: float = Field(default=7.0)
    temperature: float = Field(default=0.3)
