from pydantic import BaseModel, Field


class DocumentSynthesizerConfig(BaseModel):
    temperature: float = Field(default=0.3)
