from pydantic import BaseModel, Field

class TopicGenConfig(BaseModel):
    style: str = Field(default="", description="Content style hint")
    count: int = Field(default=5, description="Number of candidate topics")
    temperature: float = Field(default=0.8)
