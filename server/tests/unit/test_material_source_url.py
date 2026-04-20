"""Tests for Material.source_url field population in material_collector."""

import pytest
import json
from unittest.mock import AsyncMock

from src.agents.material_collector.agent import MaterialCollectorAgent
from src.agents.material_collector.schemas import MaterialCollectConfig
from src.core.state import Material


class TestMaterialSourceUrl:
    """Test that source_url is correctly populated for web and document materials."""

    @pytest.fixture
    def web_material_response(self):
        """Mock LLM response with web materials that include source_url."""
        return json.dumps([
            {
                "source": "https://example.com/article1",
                "title": "AI Tools Overview",
                "snippet": "A comprehensive review of AI tools in 2024",
                "source_type": "web",
                "source_url": "https://example.com/article1",
            },
            {
                "source": "https://example.com/article2",
                "title": "Coding with AI",
                "snippet": "How AI is changing software development",
                "source_type": "web",
                "source_url": "https://example.com/article2",
            },
        ])

    @pytest.fixture
    def web_material_missing_source_url(self):
        """Mock LLM response with web materials missing source_url (backwards compat)."""
        return json.dumps([
            {
                "source": "https://example.com/article3",
                "title": "Old Article",
                "snippet": "An article without source_url field",
                "source_type": "web",
            },
        ])

    @pytest.fixture
    def mock_model_with_source_url(self, web_material_response):
        model = AsyncMock()
        model.generate = AsyncMock(return_value=web_material_response)
        return model

    @pytest.fixture
    def mock_model_missing_source_url(self, web_material_missing_source_url):
        model = AsyncMock()
        model.generate = AsyncMock(return_value=web_material_missing_source_url)
        return model

    @pytest.mark.asyncio
    async def test_web_materials_have_source_url(self, mock_model_with_source_url):
        """Web materials returned from LLM with source_url should preserve it."""
        agent = MaterialCollectorAgent(model=mock_model_with_source_url)
        config = MaterialCollectConfig(sources=["web"], max_items=10)
        inputs = {"selected_topic": {"title": "AI Tools", "angle": "review", "score": 8.5}}

        result = await agent.run(inputs, config)

        assert "materials" in result
        assert len(result["materials"]) == 2
        for mat in result["materials"]:
            assert mat["source_type"] == "web"
            assert "source_url" in mat
            assert mat["source_url"] is not None
            assert mat["source_url"] != ""
            assert mat["source_url"].startswith("http")

    @pytest.mark.asyncio
    async def test_web_materials_missing_source_url_gets_fallback(self, mock_model_missing_source_url):
        """Web materials without source_url should get source field as fallback."""
        agent = MaterialCollectorAgent(model=mock_model_missing_source_url)
        config = MaterialCollectConfig(sources=["web"], max_items=10)
        inputs = {"selected_topic": {"title": "AI Tools", "angle": "review", "score": 8.5}}

        result = await agent.run(inputs, config)

        assert "materials" in result
        assert len(result["materials"]) == 1
        mat = result["materials"][0]
        assert mat["source_type"] == "web"
        assert mat["source_url"] is not None
        assert mat["source_url"] == mat["source"]

    @pytest.mark.asyncio
    async def test_document_materials_have_source_url(self):
        """Document materials should have source_url set to file path."""
        mock_model = AsyncMock()
        agent = MaterialCollectorAgent(model=mock_model)
        config = MaterialCollectConfig(sources=["web"], max_items=10)
        inputs = {
            "selected_topic": {"title": "Doc Topic", "angle": "test", "score": 7.0},
            "source_documents": [
                {
                    "file_path": "/docs/test.pdf",
                    "title": "Test Document",
                    "content": "This is test content for the document.",
                    "extracted_images": [],
                }
            ],
        }

        result = await agent.run(inputs, config)

        assert "materials" in result
        assert len(result["materials"]) == 1
        mat = result["materials"][0]
        assert mat["source_type"] == "document"
        assert mat["source_url"] == "/docs/test.pdf"
        assert mat["source"] == "/docs/test.pdf"

    def test_material_schema_has_source_url_field(self):
        """Material model should have source_url field."""
        mat = Material(
            source="https://example.com",
            title="Test",
            snippet="Test snippet",
            source_type="web",
            source_url="https://example.com",
        )
        assert hasattr(mat, "source_url")
        assert mat.source_url == "https://example.com"

    def test_material_schema_source_url_optional(self):
        """Material source_url should be optional (None by default for document type)."""
        mat = Material(
            source="/path/to/doc.pdf",
            title="Local Doc",
            snippet="Content",
            source_type="document",
        )
        # source_url is Optional[str] with default=None
        assert mat.source_url is None or isinstance(mat.source_url, str)
