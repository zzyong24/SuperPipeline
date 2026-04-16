"""Document Synthesizer Agent — deep analysis of user-provided source documents."""

from __future__ import annotations

import json

from pydantic import BaseModel

from src.agents.base import BaseAgent, extract_json
from src.agents.document_synthesizer.schemas import DocumentSynthesizerConfig
from src.core.state import SourceDocument


class KnowledgePoint(BaseModel):
    title: str
    content: str
    source_doc: str
    importance: float = 0.0


class CrossReference(BaseModel):
    doc_a: str
    doc_b: str
    relationship: str = ""


class DocumentSynthesizerOutput(BaseModel):
    summary: str
    knowledge_points: list[KnowledgePoint]
    cross_references: list[CrossReference]
    topic_extensions: list[str]


class DocumentSynthesizerAgent(BaseAgent):
    name = "document_synthesizer"
    consumes = ["source_documents"]
    produces = ["document_synthesizer_output"]
    config_schema = DocumentSynthesizerConfig

    async def run(self, inputs: dict, config: BaseModel) -> dict:
        cfg: DocumentSynthesizerConfig = config
        docs = [SourceDocument.model_validate(d) for d in inputs.get("source_documents", [])]

        if not docs:
            return {"document_synthesizer_output": {"summary": "", "knowledge_points": [], "cross_references": [], "topic_extensions": []}}

        prompt = self.get_prompt(
            "synthesize.j2",
            cfg,
            documents=[d.model_dump() for d in docs],
        )

        response = await self.model.generate(prompt, temperature=cfg.temperature)

        try:
            raw = json.loads(extract_json(response))
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse document_synthesizer response: {e}\nRaw: {response[:500]}") from e

        output = DocumentSynthesizerOutput.model_validate(raw)
        return {"document_synthesizer_output": output.model_dump()}
