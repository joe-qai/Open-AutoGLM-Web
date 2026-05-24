"""Shared test fixtures."""

import asyncio
import pytest_asyncio
from pathlib import Path
from app.db import db, Database


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def temp_db(tmp_path: Path):
    old_path = db.db_path
    db.db_path = str(tmp_path / "test.db")
    db._conn = None
    await db.init_db()
    yield
    db._conn = None
    db.db_path = old_path
