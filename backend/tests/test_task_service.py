"""Tests for TaskService."""

import pytest
from app.db import db
from app.services.task_service import TaskService
from app.services.script_service import ScriptService
from app.schemas.task import TaskStatus


@pytest.fixture
def task_service():
    return TaskService()


@pytest.fixture
def script_service():
    return ScriptService()


@pytest.mark.asyncio
async def test_create_and_get_task(task_service):
    task_id = await task_service.create_task(
        name="Test Task",
        description="A test task",
        platform="android",
    )
    assert task_id.startswith("task_")

    task = await task_service.get_task(task_id)
    assert task is not None
    assert task.name == "Test Task"
    assert task.description == "A test task"
    assert task.platform == "android"
    assert task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_task_not_found(task_service):
    task = await task_service.get_task("nonexistent")
    assert task is None


@pytest.mark.asyncio
async def test_create_task_with_devices(task_service):
    task_id = await task_service.create_task(
        name="Multi-device", devices=["dev-1", "dev-2"], platform="android"
    )
    task = await task_service.get_task(task_id)
    assert task is not None
    assert "dev-1" in task.devices
    assert "dev-2" in task.devices


@pytest.mark.asyncio
async def test_list_tasks(task_service):
    await task_service.create_task(name="T1", platform="android")
    await task_service.create_task(name="T2", platform="ios")

    all_tasks = await task_service.list_tasks()
    assert len(all_tasks) >= 2


@pytest.mark.asyncio
async def test_list_tasks_by_status(task_service):
    tid1 = await task_service.create_task(name="Pending", platform="android")
    tid2 = await task_service.create_task(name="Pending2", platform="android")

    pending = await task_service.list_tasks(status=TaskStatus.PENDING)
    assert len(pending) >= 2
    assert all(t.status == TaskStatus.PENDING for t in pending)


@pytest.mark.asyncio
async def test_delete_task(task_service):
    task_id = await task_service.create_task(name="Delete me", platform="android")
    await task_service.delete_task(task_id)
    task = await task_service.get_task(task_id)
    assert task is None


@pytest.mark.asyncio
async def test_delete_task_cleans_up_related_tables(task_service):
    task_id = await task_service.create_task(name="Cleanup test", devices=["d1"], platform="android")
    await task_service._log(task_id, "INFO", "test log")
    await task_service.delete_task(task_id)

    conn = await db.get_connection()
    cursor = await conn.execute("SELECT COUNT(*) as cnt FROM task_logs WHERE task_id = ?", (task_id,))
    row = await cursor.fetchone()
    assert row["cnt"] == 0

    cursor = await conn.execute("SELECT COUNT(*) as cnt FROM task_devices WHERE task_id = ?", (task_id,))
    row = await cursor.fetchone()
    assert row["cnt"] == 0


@pytest.mark.asyncio
async def test_get_task_logs(task_service):
    task_id = await task_service.create_task(name="Log test", platform="android")
    await task_service._log(task_id, "INFO", "Step 1")
    await task_service._log(task_id, "ERROR", "Something went wrong")

    logs = await task_service.get_task_logs(task_id)
    assert len(logs) == 2
    assert logs[0]["level"] == "INFO"
    assert logs[0]["message"] == "Step 1"
    assert logs[1]["level"] == "ERROR"
    assert logs[1]["message"] == "Something went wrong"


@pytest.mark.asyncio
async def test_get_task_logs_empty(task_service):
    task_id = await task_service.create_task(name="No logs", platform="android")
    logs = await task_service.get_task_logs(task_id)
    assert logs == []


@pytest.mark.asyncio
async def test_stop_nonexistent_task(task_service):
    await task_service.stop_task("nonexistent")


@pytest.mark.asyncio
async def test_execute_task_no_script_fails(task_service):
    task_id = await task_service.create_task(name="No script", platform="android")
    await task_service.execute_task(task_id)
    task = await task_service.get_task(task_id)
    assert task is not None
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_execute_task_with_script(task_service, script_service):
    script_id = await script_service.create_script(
        name="simple", content="print('hello')", script_type="manual", platform="android"
    )
    task_id = await task_service.create_task(
        name="With script", script_id=script_id, platform="android"
    )
    await task_service.execute_task(task_id)
    task = await task_service.get_task(task_id)
    assert task is not None
    assert task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)


@pytest.mark.asyncio
async def test_execute_task_creates_report(task_service, script_service):
    script_id = await script_service.create_script(
        name="report_test", content="print('report me')", script_type="manual", platform="android"
    )
    task_id = await task_service.create_task(
        name="Report test", script_id=script_id, platform="android"
    )
    await task_service.execute_task(task_id)
    conn = await db.get_connection()
    cursor = await conn.execute("SELECT html_content FROM reports WHERE task_id = ?", (task_id,))
    row = await cursor.fetchone()
    assert row is not None
    assert row["html_content"] is not None
    assert "Test Report" in row["html_content"]


@pytest.mark.asyncio
async def test_update_task_status_to_completed(task_service):
    task_id = await task_service.create_task(name="Status test", platform="android")
    await task_service._update_task_status(task_id, TaskStatus.COMPLETED)
    task = await task_service.get_task(task_id)
    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_update_task_status_sets_completed_at(task_service):
    task_id = await task_service.create_task(name="Time test", platform="android")
    await task_service._update_task_status(task_id, TaskStatus.FAILED)
    task = await task_service.get_task(task_id)
    assert task.status == TaskStatus.FAILED
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_generate_report_creates_html(task_service):
    task_id = await task_service.create_task(name="Report gen", platform="android")
    await task_service._update_task_status(task_id, TaskStatus.COMPLETED)
    await task_service._generate_report(task_id, "stdout here", "stderr here")

    conn = await db.get_connection()
    cursor = await conn.execute("SELECT * FROM reports WHERE task_id = ?", (task_id,))
    row = await cursor.fetchone()
    assert row is not None
    assert "Test Report" in row["html_content"]


@pytest.mark.asyncio
async def test_execute_task_logs_full_error_on_failure(task_service, script_service):
    """Verify that full stderr is logged without truncation."""
    # Create a script that produces a long error message
    long_error_script = """
import sys
for i in range(100):
    print(f"Error line {i}: This is a simulated error message that should not be truncated", file=sys.stderr)
sys.exit(1)
"""
    script_id = await script_service.create_script(
        name="long_error", content=long_error_script, script_type="manual", platform="android"
    )
    task_id = await task_service.create_task(
        name="Error logging test", script_id=script_id, platform="android"
    )
    await task_service.execute_task(task_id)
    task = await task_service.get_task(task_id)
    assert task.status == TaskStatus.FAILED

    logs = await task_service.get_task_logs(task_id)
    error_logs = [l for l in logs if l['level'] == 'ERROR']
    # Verify error logs contain the full message (not truncated to 500 chars)
    assert len(error_logs) > 0
    # Total error content should be longer than 500 chars (was truncated before)
    total_error_text = "".join(l['message'] for l in error_logs)
    assert len(total_error_text) > 500