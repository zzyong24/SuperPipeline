from pydantic import BaseModel, Field

class ContentGenConfig(BaseModel):
    platform: str = Field(description="Target platform name")
    format: str = Field(default="image_text")
    temperature: float = Field(default=0.7)
    style: str = Field(default="")
