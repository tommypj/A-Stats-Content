"""
Unit tests for the in-memory TaskQueue service.

Covers:
- Successful task enqueue and completion
- Task failure handling
- get_status for known / unknown task IDs
- Duplicate enqueue protection
- cleanup_old removes only completed/failed tasks beyond max_age
- stats() returns accurate counts
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest

from services.task_queue import TaskQueue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _noop():
    """Coroutine that completes successfully with no return value."""
    return None


async def _returning(value):
    """Coroutine that returns a specific value."""
    return value


async def _failing(message: str = "boom"):
    """Coroutine that raises an exception."""
    raise RuntimeError(message)


async def _slow(delay: float = 0.05):
    """Coroutine that sleeps briefly (simulates long-running work)."""
    await asyncio.sleep(delay)
    return "done"


# ---------------------------------------------------------------------------
# enqueue / get_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enqueue_returns_task_id():
    q = TaskQueue()
    tid = await q.enqueue("task-1", _noop())
    assert tid == "task-1"


@pytest.mark.asyncio
async def test_unknown_task_id_returns_none():
    q = TaskQueue()
    assert q.get_status("no-such-task") is None


@pytest.mark.asyncio
async def test_task_starts_as_running():
    q = TaskQueue()
    # Enqueue a slow task so it won't finish before we inspect
    await q.enqueue("slow-1", _slow(0.2))
    info = q.get_status("slow-1")
    assert info is not None
    assert info["status"] == "running"
    assert info["task_id"] == "slow-1"
    assert info["error"] is None


@pytest.mark.asyncio
async def test_task_completed_status():
    q = TaskQueue()
    await q.enqueue("ok-1", _noop())
    # Allow the event loop to run the task
    await asyncio.sleep(0.05)

    info = q.get_status("ok-1")
    assert info is not None
    assert info["status"] == "completed"
    assert info["completed_at"] is not None
    assert info["error"] is None


@pytest.mark.asyncio
async def test_task_result_stored():
    q = TaskQueue()
    await q.enqueue("ret-1", _returning({"answer": 42}))
    await asyncio.sleep(0.05)

    info = q.get_status("ret-1")
    assert info["status"] == "completed"
    assert info["result"] == {"answer": 42}


@pytest.mark.asyncio
async def test_task_failed_status():
    q = TaskQueue()
    await q.enqueue("fail-1", _failing("intentional failure"))
    await asyncio.sleep(0.05)

    info = q.get_status("fail-1")
    assert info is not None
    assert info["status"] == "failed"
    assert "intentional failure" in info["error"]
    assert info["completed_at"] is not None


# ---------------------------------------------------------------------------
# Duplicate enqueue protection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_enqueue_ignored_while_running():
    """Enqueueing the same task_id while it's still running should be a no-op."""
    q = TaskQueue()
    await q.enqueue("dup-1", _slow(0.3))
    # Second enqueue of same id while first is still running
    await q.enqueue("dup-1", _noop())  # should be silently ignored

    # Only one record should exist
    info = q.get_status("dup-1")
    assert info["status"] == "running"
    # Let it finish
    await asyncio.sleep(0.4)
    assert q.get_status("dup-1")["status"] == "completed"


@pytest.mark.asyncio
async def test_reenqueue_after_completion():
    """Re-using a task_id after it completed should create a fresh record."""
    q = TaskQueue()
    await q.enqueue("reuse-1", _returning("first"))
    await asyncio.sleep(0.05)
    assert q.get_status("reuse-1")["result"] == "first"

    await q.enqueue("reuse-1", _returning("second"))
    await asyncio.sleep(0.05)
    assert q.get_status("reuse-1")["result"] == "second"


# ---------------------------------------------------------------------------
# cleanup_old
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_removes_old_completed_tasks():
    q = TaskQueue()
    await q.enqueue("old-1", _noop())
    await asyncio.sleep(0.05)

    # Artificially backdate the completed_at so it appears old
    record = q._tasks["old-1"]
    record.completed_at = datetime.now(timezone.utc) - timedelta(seconds=3700)

    removed = q.cleanup_old(max_age_seconds=3600)
    assert removed == 1
    assert q.get_status("old-1") is None


@pytest.mark.asyncio
async def test_cleanup_keeps_recent_completed_tasks():
    q = TaskQueue()
    await q.enqueue("recent-1", _noop())
    await asyncio.sleep(0.05)

    removed = q.cleanup_old(max_age_seconds=3600)
    assert removed == 0
    assert q.get_status("recent-1") is not None


@pytest.mark.asyncio
async def test_cleanup_does_not_touch_running_tasks():
    q = TaskQueue()
    await q.enqueue("running-1", _slow(0.5))

    removed = q.cleanup_old(max_age_seconds=0)  # max_age=0 means anything is old
    assert removed == 0  # running task must not be removed
    assert q.get_status("running-1") is not None


@pytest.mark.asyncio
async def test_cleanup_removes_old_failed_tasks():
    q = TaskQueue()
    await q.enqueue("fail-old", _failing())
    await asyncio.sleep(0.05)

    record = q._tasks["fail-old"]
    record.completed_at = datetime.now(timezone.utc) - timedelta(seconds=7200)

    removed = q.cleanup_old(max_age_seconds=3600)
    assert removed == 1


# ---------------------------------------------------------------------------
# stats()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_counts():
    q = TaskQueue()

    # One completed
    await q.enqueue("s-complete", _noop())
    # One failed
    await q.enqueue("s-failed", _failing())
    # One still running
    await q.enqueue("s-running", _slow(0.5))

    await asyncio.sleep(0.05)

    counts = q.stats()
    assert counts["completed"] == 1
    assert counts["failed"] == 1
    assert counts["running"] == 1
    assert counts.get("pending", 0) == 0


# ---------------------------------------------------------------------------
# to_dict timestamp fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_to_dict_iso_timestamps():
    q = TaskQueue()
    await q.enqueue("ts-1", _noop())
    await asyncio.sleep(0.05)

    info = q.get_status("ts-1")
    # created_at and completed_at must be ISO-format strings
    datetime.fromisoformat(info["created_at"])
    datetime.fromisoformat(info["completed_at"])
