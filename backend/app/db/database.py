"""SQLite database module with aiosqlite."""

import aiosqlite
from pathlib import Path


class Database:
    def __init__(self, db_path: str = "./app.db"):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self):
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS scripts (
              script_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              content TEXT NOT NULL,
              script_type TEXT NOT NULL,
              platform TEXT NOT NULL,
              project_id TEXT,
              description TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              version INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              task_type TEXT DEFAULT 'functional',
              platform TEXT DEFAULT 'android',
              status TEXT DEFAULT 'pending',
              script_id TEXT REFERENCES scripts(script_id),
              device_id TEXT,
              apk_id TEXT,
              model_config_id TEXT,
              description TEXT,
              progress INTEGER DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT,
              started_at TEXT,
              completed_at TEXT
            );

            CREATE TABLE IF NOT EXISTS task_devices (
              task_id TEXT REFERENCES tasks(task_id),
              device_id TEXT,
              PRIMARY KEY (task_id, device_id)
            );

            CREATE TABLE IF NOT EXISTS task_logs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              task_id TEXT REFERENCES tasks(task_id),
              timestamp TEXT,
              level TEXT,
              message TEXT
            );

            CREATE TABLE IF NOT EXISTS projects (
              project_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT,
              platform TEXT DEFAULT 'android',
              created_at TEXT NOT NULL,
              updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS apks (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              original_filename TEXT,
              package_name TEXT,
              version TEXT,
              file_size INTEGER,
              file_path TEXT,
              upload_time TEXT NOT NULL,
              status TEXT DEFAULT 'uploaded'
            );

            CREATE TABLE IF NOT EXISTS reports (
              task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
              name TEXT,
              device_name TEXT,
              script_name TEXT,
              script_type TEXT,
              status TEXT,
              started_at TEXT,
              completed_at TEXT,
              duration_seconds INTEGER,
              html_content TEXT,
              summary TEXT,
              total_steps INTEGER,
              passed_steps INTEGER,
              failed_steps INTEGER,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS model_configs (
              config_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              provider TEXT NOT NULL, -- 'openai' or 'anthropic'
              base_url TEXT,
              api_key TEXT NOT NULL,
              model_name TEXT NOT NULL,
              is_default INTEGER DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT
            );
        """)
        
        # Add missing columns for backward compatibility
        await self._add_missing_columns()
        
        await self._conn.commit()
    
    async def _add_missing_columns(self):
        """Add missing columns to existing tables for backward compatibility."""
        # Check and add model_config_id column to tasks table
        cursor = await self._conn.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in await cursor.fetchall()]
        
        if 'model_config_id' not in columns:
            await self._conn.execute("ALTER TABLE tasks ADD COLUMN model_config_id TEXT")

    async def get_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            await self.init_db()
        return self._conn

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None


db = Database()
