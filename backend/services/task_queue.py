"""
Lightweight in-memory asyncio task queue for long-running background operations.

Design goals:
- No external dependencies (no Redis, no Celery).
- Each task is an asyncio.Task running on the same event loop.
- Caller gets back a task_id immediately; status can be polled via get_status().
- Completed tasks are cleaned up automatically to prevent unbounded memory growth.

Usage::

    from services.task_queue import task_queue

    task_id = await task_queue.enqueue("my-task-id", some_coroutine())
    info = task_queue.get_status(task_id)
    # info == {"status": "running", "result": None, "error": None, ...}
"""

import asyncio
import logging
from collections.abc import Coroutine
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ── Internal record stored per task ──────────────────────────────────────────


class _TaskRecord:
    __slots__ = (
        "task_id",
        "status",
        "result",
        "error",
        "created_at",
        "completed_at",
        "_asyncio_task",
    )

    def __init__(self, task_id: str) -> None:
        self.task_id: str = task_id
        self.status: str = "pending"  # pending | running | completed | failed
        self.result: Any = None
        self.error: str | None = None
        self.created_at: datetime = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self._asyncio_task: asyncio.Task | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ── TaskQueue class ───────────────────────────────────────────────────────────


class TaskQueue:
    """Simple in-memory asyncio task queue."""

    def __init__(self) -> None:
        self._tasks: dict[str, _TaskRecord] = {}

    # ── Public API ────────────────────────────────────────────────────────────

    async def enqueue(self, task_id: str, coro: Coroutine) -> str:
        """
        Wrap *coro* in an asyncio.Task and track its lifecycle.

        Returns the task_id so callers can poll status.  If a task with the
        same task_id already exists and is still running, the existing entry
        is reused (duplicate protection).
        """
        existing = self._tasks.get(task_id)
        if existing and existing.status in ("pending", "running"):
            logger.warning(
                "task_queue.enqueue: task %s is already %s, ignoring duplicate",
                task_id,
                existing.status,
            )
            coro.close()  # clean up the coroutine to avoid ResourceWarning
            return task_id

        record = _TaskRecord(task_id)
        record.status = "running"
        self._tasks[task_id] = record

        asyncio_task = asyncio.create_task(self._run(record, coro), name=f"tq-{task_id}")
        record._asyncio_task = asyncio_task

        logger.debug("task_queue: enqueued task %s", task_id)
        return task_id

    def get_status(self, task_id: str) -> dict[str, Any] | None:
        """
        Return the status dict for *task_id*, or None if it is unknown.
        """
        record = self._tasks.get(task_id)
        if record is None:
            return None
        return record.to_dict()

    def cleanup_old(self, max_age_seconds: int = 3600) -> int:
        """
        Remove completed/failed tasks older than *max_age_seconds*.

        Returns the number of tasks removed.
        """
        now = datetime.now(UTC)
        to_delete = [
            tid
            for tid, rec in self._tasks.items()
            if rec.status in ("completed", "failed")
            and rec.completed_at is not None
            and (now - rec.completed_at).total_seconds() > max_age_seconds
        ]
        for tid in to_delete:
            del self._tasks[tid]
        if to_delete:
            logger.debug("task_queue: cleaned up %d old tasks", len(to_delete))
        return len(to_delete)

    def stats(self) -> dict[str, int]:
        """Return counts by status (useful for health/monitoring endpoints)."""
        counts: dict[str, int] = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        for rec in self._tasks.values():
            counts[rec.status] = counts.get(rec.status, 0) + 1
        return counts

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _run(self, record: _TaskRecord, coro: Coroutine) -> None:
        """Execute *coro*, update *record* with outcome."""
        try:
            result = await coro
            record.result = result
            record.status = "completed"
        except Exception as exc:
            record.error = str(exc)
            record.status = "failed"
            logger.error("task_queue: task %s failed: %s", record.task_id, exc, exc_info=True)
        finally:
            record.completed_at = datetime.now(UTC)
            logger.debug(
                "task_queue: task %s finished with status=%s", record.task_id, record.status
            )


# ── Module-level singleton ────────────────────────────────────────────────────

task_queue = TaskQueue()
