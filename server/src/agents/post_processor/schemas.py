from pydantic import BaseModel, Field


class PostProcessorConfig(BaseModel):
    output_dir: str = Field(default="outputs")
    temperature: float = Field(default=0.3)
