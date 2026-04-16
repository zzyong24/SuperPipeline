from pydantic import BaseModel, Field


class ImageExtractorConfig(BaseModel):
    max_images: int = Field(default=20)
    temperature: float = Field(default=0.3)
