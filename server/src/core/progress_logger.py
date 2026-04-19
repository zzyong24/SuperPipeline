"""ProgressLogger — tracks and reports pipeline execution progress."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class StageProgress:
    """Progress snapshot for a single stage."""
    stage_name: str
    status: str  # "running" | "completed" | "failed" | "skipped"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error: str | None = None
    attempt: int = 1


class ProgressLogger:
    """Logs and tracks progress of pipeline execution.

    Usage:
        logger = ProgressLogger(run_id="abc123")
        logger.start_stage("content_generator")
        # ... do work ...
        logger.complete_stage("content_generator")

        # Or use context manager:
        with logger.stage("reviewer") as progress:
            # ... do work ...
            pass  # automatically logs completion
    """

    def __init__(self, run_id: str, total_stages: int = 0, verbose: bool = True, output_dir: str = "outputs") -> None:
        self.run_id = run_id
        self.total_stages = total_stages
        self.verbose = verbose
        self._stages: dict[str, StageProgress] = {}
        self._started_at: datetime | None = None
        self._completed_at: datetime | None = None
        # 新增：写文件
        self._log_file = Path(output_dir) / run_id / "progress.log"
        self._log_file.parent.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Mark pipeline start."""
        self._started_at = datetime.now()
        self._log("🚀 Pipeline started", f"run_id={self.run_id}")

    def start_stage(self, stage_name: str, attempt: int = 1) -> None:
        """Mark a stage as started."""
        progress = StageProgress(
            stage_name=stage_name,
            status="running",
            started_at=datetime.now(),
            attempt=attempt,
        )
        self._stages[stage_name] = progress
        stage_num = len(self._stages)
        msg = f"▶ Stage {stage_num}/{self.total_stages} started: {stage_name}"
        self._log(msg, f"attempt={attempt}")

    def complete_stage(self, stage_name: str, error: str | None = None) -> None:
        """Mark a stage as completed (or failed)."""
        if stage_name not in self._stages:
            self.start_stage(stage_name)

        progress = self._stages[stage_name]
        progress.completed_at = datetime.now()
        progress.duration_ms = int((progress.completed_at - progress.started_at).total_seconds() * 1000) if progress.started_at else 0

        if error:
            progress.status = "failed"
            progress.error = error
            self._log(f"✗ Stage failed: {stage_name}", f"error={error}, duration={progress.duration_ms}ms")
        else:
            progress.status = "completed"
            self._log(f"✓ Stage completed: {stage_name}", f"duration={progress.duration_ms}ms")

    def skip_stage(self, stage_name: str) -> None:
        """Mark a stage as skipped (on_error=skip)."""
        if stage_name not in self._stages:
            self._stages[stage_name] = StageProgress(stage_name=stage_name, status="skipped")
        else:
            self._stages[stage_name].status = "skipped"
        self._log(f"⊘ Stage skipped: {stage_name}")

    def complete(self, success: bool = True) -> None:
        """Mark pipeline completion."""
        self._completed_at = datetime.now()
        total_ms = int((self._completed_at - self._started_at).total_seconds() * 1000) if self._started_at else 0
        completed = sum(1 for p in self._stages.values() if p.status == "completed")
        failed = sum(1 for p in self._stages.values() if p.status == "failed")
        skipped = sum(1 for p in self._stages.values() if p.status == "skipped")

        if success:
            self._log(f"🎉 Pipeline completed", f"total_duration={total_ms}ms, completed={completed}, failed={failed}, skipped={skipped}")
        else:
            self._log(f"❌ Pipeline failed", f"total_duration={total_ms}ms, completed={completed}, failed={failed}, skipped={skipped}")

    def get_summary(self) -> dict[str, Any]:
        """Return a summary dict of the pipeline run."""
        return {
            "run_id": self.run_id,
            "total_duration_ms": int((self._completed_at - self._started_at).total_seconds() * 1000)
                if self._started_at and self._completed_at else None,
            "stages": {
                name: {
                    "status": p.status,
                    "duration_ms": p.duration_ms,
                    "error": p.error,
                    "attempt": p.attempt,
                }
                for name, p in self._stages.items()
            },
        }

    def _log(self, title: str, details: str = "") -> None:
        """Print a log line if verbose is enabled, and always write to file."""
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00"
        line = f"[{ts}] [{self.run_id}] {title}"
        if details:
            line += f" | {details}"
        # 写文件
        with open(self._log_file, "a") as f:
            f.write(line + "\n")
        # 打印
        if self.verbose:
            print(" ".join([f"[{ts}]", title, f"({details})" if details else ""]), flush=True)

    # -------------------------------------------------------------------------
    # Context manager for use in node_fn
    # -------------------------------------------------------------------------
    class _StageContext:
        """Internal context manager for a single stage."""

        def __init__(self, logger: "ProgressLogger", stage_name: str, attempt: int = 1) -> None:
            self.logger = logger
            self.stage_name = stage_name
            self.attempt = attempt
            self.error: str | None = None

        def __enter__(self) -> "_StageContext":
            self.logger.start_stage(self.stage_name, self.attempt)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
            if exc_type is not None:
                self.error = str(exc_val)
                self.logger.complete_stage(self.stage_name, error=self.error)
            # Don't suppress exceptions
            return False

    def stage(self, stage_name: str, attempt: int = 1) -> _StageContext:
        """Context manager for tracking a single stage.

        Usage:
            with logger.stage("content_generator"):
                result = await agent.run(inputs, config)
        """
        return self._StageContext(self, stage_name, attempt)
