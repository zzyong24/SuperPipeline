import pytest
from pathlib import Path
from src.storage.state_store import StateStore
from src.storage.asset_store import AssetStore


@pytest.fixture
async def state_store(tmp_path):
    store = StateStore(str(tmp_path / "test.db"))
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def asset_store(tmp_path):
    return AssetStore(
        assets_dir=str(tmp_path / "assets"),
        outputs_dir=str(tmp_path / "outputs"),
    )


@pytest.mark.asyncio
async def test_save_and_get_run(state_store):
    await state_store.save_run(
        run_id="test-run-1",
        pipeline_name="test_pipeline",
        status="running",
        state={"stage": "topic_generator"},
    )
    run = await state_store.get_run("test-run-1")
    assert run is not None
    assert run["pipeline_name"] == "test_pipeline"
    assert run["status"] == "running"


@pytest.mark.asyncio
async def test_update_run_status(state_store):
    await state_store.save_run("run-2", "test", "running", {})
    await state_store.update_run("run-2", status="completed", state={"stage": "completed"})
    run = await state_store.get_run("run-2")
    assert run["status"] == "completed"


@pytest.mark.asyncio
async def test_list_runs(state_store):
    await state_store.save_run("run-a", "pipeline_a", "completed", {})
    await state_store.save_run("run-b", "pipeline_b", "running", {})
    runs = await state_store.list_runs(limit=10)
    assert len(runs) == 2


@pytest.mark.asyncio
async def test_save_and_get_content(state_store):
    await state_store.save_content(
        content_id="content-1",
        run_id="run-1",
        platform="xiaohongshu",
        title="Test Title",
        body="Test body",
        status="pending_review",
    )
    content = await state_store.get_content("content-1")
    assert content is not None
    assert content["platform"] == "xiaohongshu"
    assert content["title"] == "Test Title"


@pytest.mark.asyncio
async def test_list_contents_by_status(state_store):
    await state_store.save_content("c1", "r1", "xiaohongshu", "T1", "B1", "approved")
    await state_store.save_content("c2", "r1", "x", "T2", "B2", "pending_review")
    approved = await state_store.list_contents(status="approved")
    assert len(approved) == 1
    assert approved[0]["content_id"] == "c1"


def test_asset_store_creates_dirs(asset_store):
    run_dir = asset_store.get_output_dir("test-run")
    assert run_dir.exists()


def test_asset_store_save_and_read(asset_store):
    output_dir = asset_store.get_output_dir("run-1")
    file_path = asset_store.save_file(output_dir, "test.txt", b"hello world")
    assert file_path.exists()
    assert file_path.read_bytes() == b"hello world"
