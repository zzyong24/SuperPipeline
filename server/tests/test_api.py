import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from src.api.app import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
@patch("src.api.routes.pipelines._list_pipelines")
async def test_list_pipelines_api(mock_list, client):
    mock_list.return_value = [{"name": "test", "stages": 3}]
    response = await client.get("/api/pipelines")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
@patch("src.api.routes.contents._list_contents")
async def test_list_contents_api(mock_list, client):
    mock_list.return_value = [
        {"content_id": "c1", "platform": "xiaohongshu", "title": "Test", "status": "approved"}
    ]
    response = await client.get("/api/contents")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
@patch("src.api.routes.runs._list_runs")
async def test_list_runs_api(mock_list, client):
    mock_list.return_value = [
        {"run_id": "abc123", "pipeline_name": "test", "status": "completed", "created_at": "2026-04-15"}
    ]
    response = await client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "abc123"


@pytest.mark.asyncio
@patch("src.api.routes.runs._get_run")
async def test_get_run_api(mock_get, client):
    mock_get.return_value = {"run_id": "abc123", "status": "completed", "state": {}}
    response = await client.get("/api/runs/abc123")
    assert response.status_code == 200
    assert response.json()["run_id"] == "abc123"
