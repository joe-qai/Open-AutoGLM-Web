"""SQLite-backed APK metadata service for persisting original filenames."""

import sqlite3
import threading
from typing import List, Optional
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "apk_metadata.db"


class ApkMetadataService:
    """Singleton service that stores APK metadata in SQLite."""

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
            CREATE TABLE IF NOT EXISTS apk_metadata (
                apk_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                package_name TEXT,
                version TEXT,
                file_size INTEGER,
                upload_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploaded'
            )
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection (one per write for thread safety)."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def save(
        self,
        apk_id: str,
        original_filename: str,
        package_name: Optional[str] = None,
        version: Optional[str] = None,
        file_size: Optional[int] = None,
        upload_time: str,
        status: str = "uploaded",
    ) -> str:
        """Save APK metadata to SQLite. Returns the apk_id."""
        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO apk_metadata
                   (apk_id, original_filename, package_name, version,
                    file_size, upload_time, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (apk_id, original_filename, package_name, version,
                 file_size, upload_time, status),
            )
            conn.commit()
        finally:
            conn.close()

        return apk_id

    def get(self, apk_id: str) -> Optional[dict]:
        """Get APK metadata by apk_id."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM apk_metadata WHERE apk_id = ?",
                (apk_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_all(self) -> List[dict]:
        """List all APK metadata entries."""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM apk_metadata ORDER BY upload_time DESC"
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete(self, apk_id: str) -> bool:
        """Delete APK metadata by apk_id."""
        conn = self._get_conn()
        try:
            conn.execute(
                "DELETE FROM apk_metadata WHERE apk_id = ?",
                (apk_id,),
            )
            conn.commit()
        finally:
            conn.close()

        return True

    def update_status(self, apk_id: str, status: str) -> bool:
        """Update the status of an APK metadata entry."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE apk_metadata SET status = ? WHERE apk_id = ?",
                (status, apk_id),
            )
            conn.commit()
        finally:
            conn.close()

        return True