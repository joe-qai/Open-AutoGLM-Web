"""Tests for ReportService."""

import pytest
from app.services.report_service import ReportService


@pytest.fixture
def service():
    return ReportService()


@pytest.mark.asyncio
async def test_list_reports_empty(service):
    reports = await service.list_reports()
    assert reports == []


@pytest.mark.asyncio
async def test_get_report_not_found(service):
    report = await service.get_report("nonexistent")
    assert report is None


@pytest.mark.asyncio
async def test_get_report_html_not_found(service):
    html = await service.get_report_html("nonexistent")
    assert html is None


@pytest.mark.asyncio
async def test_delete_report_nonexistent(service):
    await service.delete_report("nonexistent")


@pytest.mark.asyncio
async def test_insert_and_get_report(service):
    from app.db import db
    conn = await db.get_connection()
    await conn.execute(
        """INSERT INTO reports (task_id, name, status, html_content, summary, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("r-1", "Test Report", "passed", "<html>ok</html>", "All good", "2026-01-01T00:00:00")
    )
    await conn.commit()

    reports = await service.list_reports()
    assert len(reports) >= 1
    r = reports[0]
    assert r["task_id"] == "r-1"
    assert r["name"] == "Test Report"
    assert "html_content" not in r

    report = await service.get_report("r-1")
    assert report is not None
    assert report["name"] == "Test Report"


@pytest.mark.asyncio
async def test_get_report_html(service):
    from app.db import db
    conn = await db.get_connection()
    await conn.execute(
        """INSERT INTO reports (task_id, name, status, html_content, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        ("r-html", "HTML Report", "passed", "<html>content</html>", "2026-01-01T00:00:00")
    )
    await conn.commit()

    html = await service.get_report_html("r-html")
    assert html == "<html>content</html>"


@pytest.mark.asyncio
async def test_list_reports_filtered(service):
    from app.db import db
    conn = await db.get_connection()
    await conn.execute(
        """INSERT INTO reports (task_id, name, status, created_at) VALUES (?, ?, ?, ?)""",
        ("f-1", "Failed Report", "failed", "2026-01-01T00:00:00")
    )
    await conn.execute(
        """INSERT INTO reports (task_id, name, status, created_at) VALUES (?, ?, ?, ?)""",
        ("f-2", "Passed Report", "passed", "2026-01-02T00:00:00")
    )
    await conn.commit()

    failed = await service.list_reports(status="failed")
    assert len(failed) == 1
    assert failed[0]["task_id"] == "f-1"

    by_task = await service.list_reports(task_id="f-2")
    assert len(by_task) == 1
    assert by_task[0]["task_id"] == "f-2"


@pytest.mark.asyncio
async def test_delete_report(service):
    from app.db import db
    conn = await db.get_connection()
    await conn.execute(
        """INSERT INTO reports (task_id, name, status, created_at) VALUES (?, ?, ?, ?)""",
        ("del-me", "Delete me", "passed", "2026-01-01T00:00:00")
    )
    await conn.commit()

    await service.delete_report("del-me")
    report = await service.get_report("del-me")
    assert report is None


@pytest.mark.asyncio
async def test_batch_delete(service):
    from app.db import db
    conn = await db.get_connection()
    for i in range(3):
        await conn.execute(
            """INSERT INTO reports (task_id, name, status, created_at) VALUES (?, ?, ?, ?)""",
            (f"b-{i}", f"Batch {i}", "passed", "2026-01-01T00:00:00")
        )
    await conn.commit()

    deleted, failed = await service.batch_delete(["b-0", "b-1", "nonexistent"])
    assert deleted == 2
    assert failed == ["nonexistent"]


@pytest.mark.asyncio
async def test_batch_delete_nonexistent_all(service):
    deleted, failed = await service.batch_delete(["no1", "no2"])
    assert deleted == 0
    assert failed == ["no1", "no2"]
