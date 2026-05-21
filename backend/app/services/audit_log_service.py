"""SQLite-backed audit log service for recording all system operations."""

import sqlite3
import json
import time
import uuid
import threading
from typing import List, Optional, Any
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "audit_log.db"


class AuditLogService:
    """Singleton service that writes log entries to SQLite."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create tables."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                log_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                action TEXT NOT NULL,
                operator TEXT NOT NULL,
                target_id TEXT,
                target_name TEXT,
                detail TEXT,
                device_id TEXT,
                script_id TEXT,
                task_id TEXT,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                duration_ms INTEGER,
                error TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_category ON logs(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_device ON logs(device_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_script ON logs(script_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id)")
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection (one per write for thread safety)."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def log(
        self,
        level: str = "info",
        category: str = "system",
        action: str = "created",
        operator: str = "system",
        target_id: Optional[str] = None,
        target_name: Optional[str] = None,
        detail: Optional[dict] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> str:
        """Write a log entry to SQLite. Returns the log_id."""
        log_id = f"log_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        detail_json = json.dumps(detail) if detail else None

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT INTO logs (log_id, timestamp, level, category, action, operator,
                   target_id, target_name, detail, device_id, script_id, task_id,
                   endpoint, method, status_code, duration_ms, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (log_id, timestamp, level, category, action, operator,
                 target_id, target_name, detail_json, device_id, script_id, task_id,
                 endpoint, method, status_code, duration_ms, error),
            )
            conn.commit()
        finally:
            conn.close()

        return log_id

    def list_logs(
        self,
        level: Optional[str] = None,
        category: Optional[str] = None,
        device_id: Optional[str] = None,
        script_id: Optional[str] = None,
        task_id: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """Query logs with filters."""
        conn = self._get_conn()
        try:
            query = "SELECT * FROM logs WHERE 1=1"
            params = []

            if level:
                query += " AND level = ?"
                params.append(level)
            if category:
                query += " AND category = ?"
                params.append(category)
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            if script_id:
                query += " AND script_id = ?"
                params.append(script_id)
            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)
            if search:
                query += " AND (target_name LIKE ? OR error LIKE ? OR detail LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, skip])

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_summary(self) -> dict:
        """Get aggregated log statistics."""
        conn = self._get_conn()
        try:
            total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            error_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'error'").fetchone()[0]
            warning_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'warning'").fetchone()[0]
            info_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'info'").fetchone()[0]
            debug_count = conn.execute("SELECT COUNT(*) FROM logs WHERE level = 'debug'").fetchone()[0]

            avg_result = conn.execute(
                "SELECT AVG(duration_ms) FROM logs WHERE duration_ms IS NOT NULL AND category = 'api'"
            ).fetchone()[0]

            return {
                "total": total,
                "error_count": error_count,
                "warning_count": warning_count,
                "info_count": info_count,
                "debug_count": debug_count,
                "avg_response_time_ms": avg_result,
            }
        finally:
            conn.close()

    def clear_logs(self):
        """Delete all logs from the database."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM logs")
            conn.commit()
        finally:
            conn.close()