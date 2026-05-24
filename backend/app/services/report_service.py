"""Report service for managing reports — SQLite persistence."""

from typing import List, Optional
import time

from app.db import db


class ReportService:

    async def list_reports(
        self,
        task_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        conn = await db.get_connection()
        conditions = []
        params = []
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        cursor = await conn.execute(
            f"""SELECT 
                    r.task_id AS report_id, 
                    r.task_id, 
                    r.name, 
                    r.name AS task_name, 
                    t.platform, 
                    r.device_name, 
                    r.script_name, 
                    r.script_type, 
                    r.status, 
                    r.started_at, 
                    r.completed_at, 
                    r.duration_seconds AS duration, 
                    r.summary, 
                    r.created_at,
                    'html' as report_type
                FROM reports r
                LEFT JOIN tasks t ON r.task_id = t.task_id
                {where} 
                ORDER BY r.created_at DESC 
                LIMIT ? OFFSET ?""",
            params + [limit, skip]
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_report(self, report_id: str) -> Optional[dict]:
        conn = await db.get_connection()
        cursor = await conn.execute(
            """SELECT 
                    r.task_id AS report_id, 
                    r.task_id, 
                    r.name, 
                    r.name AS task_name, 
                    t.platform, 
                    r.device_name, 
                    r.script_name, 
                    r.script_type, 
                    r.status, 
                    r.started_at, 
                    r.completed_at, 
                    r.duration_seconds AS duration, 
                    r.summary, 
                    r.created_at,
                    'html' as report_type
                FROM reports r
                LEFT JOIN tasks t ON r.task_id = t.task_id
                WHERE r.task_id = ?""",
            (report_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_report_html(self, task_id: str) -> Optional[str]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT html_content FROM reports WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        return row["html_content"] if row else None

    async def delete_report(self, report_id: str):
        conn = await db.get_connection()
        await conn.execute("DELETE FROM reports WHERE task_id = ?", (report_id,))
        await conn.commit()

    async def batch_delete(self, report_ids: list[str]) -> tuple[int, list[str]]:
        conn = await db.get_connection()
        deleted = 0
        failed = []
        for report_id in report_ids:
            cursor = await conn.execute("DELETE FROM reports WHERE task_id = ?", (report_id,))
            if cursor.rowcount > 0:
                deleted += 1
            else:
                failed.append(report_id)
        await conn.commit()
        return deleted, failed
