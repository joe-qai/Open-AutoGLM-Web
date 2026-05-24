"""Tests for the Database module."""

import pytest
from app.db import db, Database


@pytest.mark.asyncio
async def test_init_db_creates_tables():
    conn = await db.get_connection()
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = {row["name"] for row in await cursor.fetchall()}
    expected = {"scripts", "tasks", "task_devices", "task_logs", "projects", "apks", "reports"}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


@pytest.mark.asyncio
async def test_get_connection_returns_same_connection():
    conn1 = await db.get_connection()
    conn2 = await db.get_connection()
    assert conn1 is conn2


@pytest.mark.asyncio
async def test_close_resets_connection():
    conn = await db.get_connection()
    await db.close()
    assert db._conn is None
    conn_after = await db.get_connection()
    assert conn_after is not None
    assert conn_after is not conn


@pytest.mark.asyncio
async def test_database_custom_path(tmp_path):
    custom_path = str(tmp_path / "custom.db")
    d = Database(custom_path)
    assert d.db_path == custom_path
    assert d._conn is None
    await d.close()
