"""Task service for managing tasks — SQLite persistence + subprocess executor."""

from typing import List, Optional, Dict
import time
import subprocess
import tempfile
import datetime
import os
import sys

from app.config import settings
from app.db import db
from app.schemas.task import TaskResponse, TaskStatus, TaskType


class TaskService:

    def __init__(self):
        self.task_processes: Dict[str, subprocess.Popen] = {}
        self.task_errors: Dict[str, str] = {}

    async def create_task(
        self,
        name: str,
        task_type: Optional[str] = None,
        platform: Optional[str] = None,
        devices: Optional[List[str]] = None,
        steps: Optional[List[Dict]] = None,
        description: Optional[str] = None,
        script_id: Optional[str] = None,
        device_id: Optional[str] = None,
        apk_id: Optional[str] = None,
    ) -> str:
        task_id = f"task_{int(time.time_ns())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO tasks (task_id, name, task_type, platform, status, script_id, device_id, apk_id, description, progress, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (task_id, name, task_type or "functional", platform or "android",
             TaskStatus.PENDING.value, script_id, device_id, apk_id, description,
             timestamp, timestamp)
        )
        await conn.commit()
        if devices:
            for device_id in devices:
                await conn.execute(
                    "INSERT OR IGNORE INTO task_devices (task_id, device_id) VALUES (?, ?)",
                    (task_id, device_id)
                )
            await conn.commit()
        return task_id

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        dev_cursor = await conn.execute("SELECT device_id FROM task_devices WHERE task_id = ?", (task_id,))
        dev_rows = await dev_cursor.fetchall()
        device_ids = [r["device_id"] for r in dev_rows]
        result = TaskResponse(
            task_id=row["task_id"],
            name=row["name"],
            task_type=TaskType(row["task_type"]) if row["task_type"] in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
            platform=row["platform"],
            devices=device_ids,
            status=TaskStatus(row["status"]),
            description=row["description"],
            script_id=row["script_id"],
            device_id=row["device_id"],
            apk_id=row["apk_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"]
        )
        result.error_message = self.task_errors.get(task_id)
        return result

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[TaskResponse]:
        conn = await db.get_connection()
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        cursor = await conn.execute(
            f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, skip]
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            task_resp = TaskResponse(
                task_id=row["task_id"],
                name=row["name"],
                task_type=TaskType(row["task_type"]) if row["task_type"] in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
                platform=row["platform"],
                devices=[],
                status=TaskStatus(row["status"]),
                description=row["description"],
                script_id=row["script_id"],
                device_id=row["device_id"],
                apk_id=row["apk_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                started_at=row["started_at"],
                completed_at=row["completed_at"]
            )
            task_resp.error_message = self.task_errors.get(row["task_id"])
            result.append(task_resp)
        return result

    async def _get_script_content(self, script_id: str) -> Optional[str]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT content FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        return row["content"] if row else None

    async def execute_task(self, task_id: str):
        task = await self.get_task(task_id)
        if not task:
            return
        conn = await db.get_connection()
        await conn.execute(
            "UPDATE tasks SET status = ?, started_at = ?, updated_at = ? WHERE task_id = ?",
            (TaskStatus.EXECUTING.value, time.strftime("%Y-%m-%dT%H:%M:%S"),
             time.strftime("%Y-%m-%dT%H:%M:%S"), task_id)
        )
        await conn.commit()
        await self._log(task_id, "INFO", "Starting task execution via subprocess")

        if not task.script_id:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", "No script associated with task")
            return

        script_content = await self._get_script_content(task.script_id)
        if not script_content:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", "Script not found")
            return

        temp_script_path = None
        try:
            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(
                suffix='.py', delete=False, prefix=f'task_{task_id}_', mode='w', encoding='utf-8'
            ) as temp_script:
                temp_script.write(script_content)
                temp_script_path = temp_script.name
            
            await self._log(task_id, "INFO", f"Created temp script file: {temp_script_path}")

            # 构建环境变量
            env_vars = os.environ.copy()
            if task.device_id:
                env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id
            env_vars['PHONE_AGENT_BASE_URL'] = settings.model_api_url
            env_vars['PHONE_AGENT_MODEL'] = settings.model_name
            env_vars['PHONE_AGENT_API_KEY'] = settings.api_key
            
            # Compute project root for subprocess cwd (still needed as working directory)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))

            # Don't override PYTHONPATH — let the venv Python resolve packages naturally
            # The script's imports are resolved via the venv's site-packages

            # Add diagnostic logging before subprocess launch
            await self._log(task_id, "INFO", f"Python executable: {sys.executable}")
            await self._log(task_id, "INFO", f"Device ID: {task.device_id}")
            await self._log(task_id, "INFO", f"Script content length: {len(script_content)} chars")
            await self._log(task_id, "INFO", f"Script first 3 lines: {chr(10).join(script_content.split(chr(10))[:3])}")

            # Use the venv Python that's already running the backend
            python_executable = sys.executable

            # 启动子进程执行脚本
            process = subprocess.Popen(
                [python_executable, temp_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env_vars,
                cwd=project_root,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            self.task_processes[task_id] = process
            
            await self._log(task_id, "INFO", f"Subprocess started with PID: {process.pid}")

            # 等待进程完成
            stdout, stderr = process.communicate()

            await self._log(task_id, "INFO", f"Subprocess completed with return code: {process.returncode}")

            if process.returncode == 0:
                await self._update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
                await self._log(task_id, "INFO", "Task completed successfully")
                if stdout:
                    # Log stdout in chunks to avoid single huge entry
                    for i in range(0, len(stdout), 2000):
                        chunk = stdout[i:i+2000]
                        await self._log(task_id, "INFO", f"Output: {chunk}")
            else:
                await self._update_task_status(task_id, TaskStatus.FAILED, progress=100)
                error_msg = stderr[:2000] if stderr else "Unknown error"
                self.task_errors[task_id] = error_msg
                # Log full error — split into chunks if very long
                if len(error_msg) > 2000:
                    for i in range(0, len(error_msg), 2000):
                        chunk = error_msg[i:i+2000]
                        await self._log(task_id, "ERROR", f"Error detail (part {i//2000+1}): {chunk}")
                else:
                    await self._log(task_id, "ERROR", f"Task failed: {error_msg}")

            await self._generate_report(
                task_id,
                stdout if stdout else "",
                stderr if stderr else ""
            )
        except Exception as e:
            error_msg = f"Subprocess error: {str(e)}"
            self.task_errors[task_id] = error_msg
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", error_msg)
        finally:
            # 清理临时脚本文件
            if temp_script_path and os.path.exists(temp_script_path):
                os.unlink(temp_script_path)
            # 移除任务进程记录
            self.task_processes.pop(task_id, None)

    async def _generate_report(self, task_id: str, stdout: str, stderr: str):
        task = await self.get_task(task_id)
        if not task:
            return

        if task.status == TaskStatus.COMPLETED:
            status_text = "passed"
        elif task.status == TaskStatus.STOPPED:
            status_text = "stopped"
        else:
            status_text = "failed"

        # Capture screenshot on error only (not on success)
        screenshot_base64 = None
        if task.status in (TaskStatus.FAILED, TaskStatus.STOPPED) and task.device_id:
            from app.services.device_service import DeviceService
            device_service = DeviceService()
            try:
                screenshot_base64 = device_service.get_screenshot(task.device_id)
            except Exception:
                screenshot_base64 = None

        started = task.started_at or task.created_at
        completed = task.completed_at or time.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            start_dt = datetime.datetime.fromisoformat(started)
            end_dt = datetime.datetime.fromisoformat(completed)
            duration = int((end_dt - start_dt).total_seconds())
        except Exception:
            duration = 0

        logs = await self.get_task_logs(task_id)
        step_rows = ""
        for i, log in enumerate(logs[:50]):
            step_rows += f"<tr><td>{i+1}</td><td>{log['timestamp']}</td><td>{log['level']}</td><td>{log['message']}</td></tr>\n"

        # Build screenshot section if available
        screenshot_section = ""
        if screenshot_base64:
            screenshot_section = f"""
        <h2>Error Screenshot</h2>
        <div style="background:#1e293b;padding:12px;border-radius:8px;border:1px solid #334155;margin:16px 0;">
          <img src="data:image/png;base64,{screenshot_base64}"
               style="max-width:100%;border-radius:4px;" alt="Error Screenshot" />
        </div>
        """

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>Test Report - {task.name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
h1 {{ color: #fff; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
h2 {{ color: #e2e8f0; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #334155; }}
th {{ background: #1e293b; color: #94a3b8; }}
.status-passed {{ color: #3ddc84; }}
.status-failed {{ color: #ef4444; }}
.status-stopped {{ color: #f59e0b; }}
.summary {{ display: flex; gap: 16px; margin: 16px 0; }}
.summary-item {{ background: #1e293b; padding: 12px 20px; border-radius: 8px; border: 1px solid #334155; }}
</style></head>
<body>
<h1>Test Report: {task.name}</h1>
<div class="summary">
  <div class="summary-item"><strong>Status:</strong> <span class="status-{status_text}">{status_text}</span></div>
  <div class="summary-item"><strong>Duration:</strong> {duration}s</div>
  <div class="summary-item"><strong>Started:</strong> {started}</div>
  <div class="summary-item"><strong>Completed:</strong> {completed}</div>
</div>
{screenshot_section}
<h2>Execution Log</h2>
<table><thead><tr><th>#</th><th>Time</th><th>Level</th><th>Message</th></tr></thead><tbody>
{step_rows}
</tbody></table>
</body></html>"""

        conn = await db.get_connection()
        await conn.execute(
            """INSERT OR REPLACE INTO reports (task_id, name, device_name, script_name, script_type, status, started_at, completed_at, duration_seconds, html_content, summary, total_steps, passed_steps, failed_steps, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task_id, task.name, task.device_id, task.script_id, "", status_text,
             started, completed, duration, html_content,
             f"Total steps: {len(logs)}", len(logs),
             len([l for l in logs if l['level'] == 'INFO']),
             len([l for l in logs if l['level'] == 'ERROR']),
             time.strftime("%Y-%m-%dT%H:%M:%S"))
        )
        await conn.commit()

    async def _update_task_status(self, task_id: str, status: TaskStatus, progress: Optional[int] = None):
        conn = await db.get_connection()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.STOPPED):
            await conn.execute(
                "UPDATE tasks SET status = ?, completed_at = ?, updated_at = ?, progress = COALESCE(?, progress) WHERE task_id = ?",
                (status.value, now, now, progress, task_id)
            )
        else:
            await conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ?, progress = COALESCE(?, progress) WHERE task_id = ?",
                (status.value, now, progress, task_id)
            )
        await conn.commit()

    async def stop_task(self, task_id: str):
        task = await self.get_task(task_id)
        if not task:
            return
        process = self.task_processes.get(task_id)
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            del self.task_processes[task_id]
        await self._update_task_status(task_id, TaskStatus.STOPPED)
        await self._log(task_id, "INFO", "Task stopped by user")

    async def delete_task(self, task_id: str):
        self.task_errors.pop(task_id, None)
        process = self.task_processes.get(task_id)
        if process:
            process.kill()
            del self.task_processes[task_id]
        conn = await db.get_connection()
        await conn.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM task_devices WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))
        await conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        await conn.commit()

    async def batch_delete(self, task_ids: list[str]) -> tuple[int, list[str]]:
        conn = await db.get_connection()
        deleted = 0
        failed = []
        try:
            await conn.execute("BEGIN")
            for task_id in task_ids:
                self.task_errors.pop(task_id, None)
                process = self.task_processes.get(task_id)
                if process:
                    process.kill()
                    del self.task_processes[task_id]
                await conn.execute("DELETE FROM task_logs WHERE task_id = ?", (task_id,))
                await conn.execute("DELETE FROM task_devices WHERE task_id = ?", (task_id,))
                await conn.execute("DELETE FROM reports WHERE task_id = ?", (task_id,))
                cursor = await conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
                if cursor.rowcount > 0:
                    deleted += 1
                else:
                    failed.append(task_id)
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        return deleted, failed

    async def _log(self, task_id: str, level: str, message: str):
        conn = await db.get_connection()
        await conn.execute(
            "INSERT INTO task_logs (task_id, timestamp, level, message) VALUES (?, ?, ?, ?)",
            (task_id, time.strftime("%Y-%m-%dT%H:%M:%S"), level, message)
        )
        await conn.commit()

    async def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict]:
        conn = await db.get_connection()
        cursor = await conn.execute(
            "SELECT timestamp, level, message FROM task_logs WHERE task_id = ? ORDER BY id DESC LIMIT ?",
            (task_id, limit)
        )
        rows = await cursor.fetchall()
        logs = []
        for row in reversed(rows):
            logs.append({
                "timestamp": row["timestamp"],
                "level": row["level"],
                "message": row["message"]
            })
        return logs
