"""File-based storage for content assets (images, generated files)."""

from __future__ import annotations

from pathlib import Path


class AssetStore:
    def __init__(self, assets_dir: str, outputs_dir: str) -> None:
        self.assets_dir = Path(assets_dir)
        self.outputs_dir = Path(outputs_dir)

    def get_asset_dir(self, run_id: str) -> Path:
        d = self.assets_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_output_dir(self, run_id: str) -> Path:
        d = self.outputs_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_file(self, directory: Path, filename: str, data: bytes) -> Path:
        file_path = directory / filename
        file_path.write_bytes(data)
        return file_path

    def read_file(self, file_path: Path) -> bytes:
        return file_path.read_bytes()

    def list_files(self, directory: Path) -> list[Path]:
        if not directory.exists():
            return []
        return sorted(f for f in directory.iterdir() if f.is_file())
