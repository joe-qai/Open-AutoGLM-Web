"""Task service for managing tasks — SQLite persistence + ScriptExecutor."""

from typing import List, Optional, Dict
import asyncio
import time
import datetime
import os
import sys
import traceback

from fastapi import BackgroundTasks
from app.config import settings
from app.db import db
from app.schemas.task import TaskResponse, TaskStatus, TaskType
from app.core.executors import ScriptExecutor, TaskDispatcher



class TaskService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskService, cls).__new__(cls)
            cls._instance.task_processes = {}
            cls._instance.task_errors = {}
        return cls._instance

    def __init__(self):
        # Already initialized in __new__
        pass

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
        model_config_id: Optional[str] = None,
    ) -> str:
        task_id = f"task_{int(time.time_ns())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO tasks (task_id, name, task_type, platform, status, script_id, device_id, apk_id, model_config_id, description, progress, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
            (task_id, name, task_type or "functional", platform or "android",
             TaskStatus.PENDING.value, script_id, device_id, apk_id, model_config_id, description,
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
        # Convert row to dict for safe field access
        row_dict = dict(row) if row else {}
        result = TaskResponse(
            task_id=row_dict.get("task_id", ""),
            name=row_dict.get("name", ""),
            task_type=TaskType(row_dict.get("task_type")) if row_dict.get("task_type") in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
            platform=row_dict.get("platform", "android"),
            devices=device_ids,
            status=TaskStatus(row_dict.get("status", "pending")),
            description=row_dict.get("description"),
            script_id=row_dict.get("script_id"),
            device_id=row_dict.get("device_id"),
            apk_id=row_dict.get("apk_id"),
            model_config_id=row_dict.get("model_config_id"),
            created_at=row_dict.get("created_at"),
            updated_at=row_dict.get("updated_at"),
            started_at=row_dict.get("started_at"),
            completed_at=row_dict.get("completed_at")
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
            row_dict = dict(row) if row else {}
            task_resp = TaskResponse(
                task_id=row_dict.get("task_id", ""),
                name=row_dict.get("name", ""),
                task_type=TaskType(row_dict.get("task_type")) if row_dict.get("task_type") in TaskType._value2member_map_ else TaskType.FUNCTIONAL,
                platform=row_dict.get("platform", "android"),
                devices=[],
                status=TaskStatus(row_dict.get("status", "pending")),
                description=row_dict.get("description"),
                script_id=row_dict.get("script_id"),
                device_id=row_dict.get("device_id"),
                apk_id=row_dict.get("apk_id"),
                model_config_id=row_dict.get("model_config_id"),
                created_at=row_dict.get("created_at"),
                updated_at=row_dict.get("updated_at"),
                started_at=row_dict.get("started_at"),
                completed_at=row_dict.get("completed_at")
            )
            task_resp.error_message = self.task_errors.get(row_dict.get("task_id"))
            result.append(task_resp)
        return result

    async def _get_script_content(self, script_id: str) -> Optional[str]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT content FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        return row["content"] if row else None

    async def _get_script_content_full(self, script_id: str) -> Optional[dict]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

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
        await self._log(task_id, "INFO", "Starting task execution via ScriptExecutor")

        if not task.script_id:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", "No script associated with task")
            return

        script_content = await self._get_script_content(task.script_id)
        if not script_content:
            await self._update_task_status(task_id, TaskStatus.FAILED)
            await self._log(task_id, "ERROR", "Script not found")
            return

        try:
            # Build environment variables for ScriptExecutor
            env_vars = {}
            
            from app.services.model_config_service import ModelConfigService
            model_service = ModelConfigService()
            model_config = None
            if task.model_config_id:
                model_config = await model_service.get_config(task.model_config_id)
            if not model_config:
                model_config = await model_service.get_default_config()
            
            if model_config:
                env_vars['PHONE_AGENT_BASE_URL'] = model_config.base_url or ""
                env_vars['PHONE_AGENT_MODEL'] = model_config.model_name
                env_vars['PHONE_AGENT_API_KEY'] = model_config.api_key
                env_vars['PHONE_AGENT_PROVIDER'] = model_config.provider.value
            else:
                env_vars['PHONE_AGENT_BASE_URL'] = "http://localhost:8000/v1"
                env_vars['PHONE_AGENT_MODEL'] = "AutoPhone-phone-9b"
                env_vars['PHONE_AGENT_API_KEY'] = "EMPTY"
            
            if task.device_id:
                env_vars['PHONE_AGENT_DEVICE_ID'] = task.device_id

            # Add diagnostic logging before execution
            await self._log(task_id, "INFO", f"Python executable: {sys.executable}")
            await self._log(task_id, "INFO", f"Device ID: {task.device_id}")
            await self._log(task_id, "INFO", f"Script content length: {len(script_content)} chars")
            await self._log(task_id, "INFO", f"Script first 3 lines: {chr(10).join(script_content.split(chr(10))[:3])}")

            # Create ScriptExecutor instance
            executor = ScriptExecutor()
            
            # Start execution (non-blocking)
            process = executor.start(
                script_content=script_content,
                env_vars=env_vars
            )
            self.task_processes[task_id] = process
            
            await self._log(task_id, "INFO", f"Subprocess started with PID: {process.pid}")

            # Store event loop reference for cancel check
            loop = asyncio.get_running_loop()
            
            # Define cancel check callback
            def cancel_check():
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.get_task(task_id), loop
                    )
                    current_task = future.result(timeout=1.0)
                    return current_task and current_task.status == TaskStatus.STOPPED
                except Exception:
                    return False

            # Wait for completion with cancel support
            result = executor.wait(cancel_check=cancel_check)

            await self._log(task_id, "INFO", f"Execution completed with status: {result.status}")

            # Log executor logs
            for log_entry in result.logs:
                await self._log(task_id, log_entry.level, log_entry.message)

            # Re-fetch task to check if it was stopped by user
            updated_task = await self.get_task(task_id)
            if not updated_task:
                return

            if updated_task.status == TaskStatus.STOPPED:
                await self._log(task_id, "INFO", "Task was stopped by user, keeping STOPPED status")
            elif result.status == "success":
                await self._update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
                await self._log(task_id, "INFO", "Task completed successfully")
                if result.stdout:
                    for i in range(0, len(result.stdout), 2000):
                        chunk = result.stdout[i:i+2000]
                        await self._log(task_id, "INFO", f"Output: {chunk}")
            else:
                await self._update_task_status(task_id, TaskStatus.FAILED, progress=100)
                error_msg = result.error_message or (result.stderr[:2000] if result.stderr else "Unknown error")
                self.task_errors[task_id] = error_msg
                if len(error_msg) > 2000:
                    for i in range(0, len(error_msg), 2000):
                        chunk = error_msg[i:i+2000]
                        await self._log(task_id, "ERROR", f"Error detail (part {i//2000+1}): {chunk}")
                else:
                    await self._log(task_id, "ERROR", f"Task failed: {error_msg}")

            # Re-fetch task again to get final status for report decision
            final_task = await self.get_task(task_id)
            if not final_task:
                return

            should_generate_report = True
            if final_task.status == TaskStatus.STOPPED:
                should_generate_report = False
                await self._log(task_id, "INFO", "Skipping report generation for stopped task")
            elif final_task.status == TaskStatus.FAILED and final_task.script_id:
                script_content_full = await self._get_script_content_full(final_task.script_id)
                if script_content_full and script_content_full.get("script_type") != "ai_generated":
                    should_generate_report = False
                    await self._log(task_id, "INFO", "Skipping report generation for non-AI script on failure")

            if should_generate_report:
                await self._generate_report(
                    task_id,
                    result.stdout if result.stdout else "",
                    result.stderr if result.stderr else ""
                )
        except Exception as e:
            full_tb = traceback.format_exc()
            error_msg = f"ScriptExecutor error: {str(e)}\n{full_tb}"
            self.task_errors[task_id] = f"ScriptExecutor error: {str(e)}"
            await self._update_task_status(task_id, TaskStatus.FAILED)
            for i in range(0, len(error_msg), 2000):
                await self._log(task_id, "ERROR", error_msg[i:i+2000])
        finally:
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
            try:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
            except Exception as e:
                print(f"Error stopping task {task_id}: {e}")
            finally:
                self.task_processes.pop(task_id, None)
        await self._update_task_status(task_id, TaskStatus.STOPPED)
        await self._log(task_id, "INFO", "Task stopped by user")

    async def delete_task(self, task_id: str):
        self.task_errors.pop(task_id, None)
        process = self.task_processes.get(task_id)
        if process:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            self.task_processes.pop(task_id, None)
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
                    try:
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
                    self.task_processes.pop(task_id, None)
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
    
    async def execute_natural_language_task(
        self,
        task_description: str,
        device_id: Optional[str],
        platform: Optional[str],
        max_steps: int,
        mode: str,
        save_task: bool = True,
        background_tasks: BackgroundTasks = None,
    ) -> str:
        """Execute a task using natural language via AgentEngine.
        
        Args:
            save_task: If True, save task record to database. If False, skip recording.
        """
        task_id = f"task_{int(time.time_ns())}"
        
        if save_task:
            conn = await db.get_connection()
            await conn.execute(
                """INSERT INTO tasks (task_id, name, task_type, platform, status, device_id, description, progress, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)""",
                (task_id, task_description[:100] + "...", "natural_language", platform or "android",
                 TaskStatus.EXECUTING.value, device_id, task_description,
                 time.strftime("%Y-%m-%dT%H:%M:%S"), time.strftime("%Y-%m-%dT%H:%M:%S"))
            )
            await conn.commit()
            await self._log(task_id, "INFO", f"Starting natural language task: {task_description}")
        
        # Run in background to avoid blocking the API response
        if background_tasks:
            background_tasks.add_task(
                self._execute_natural_language_task_bg,
                task_id,
                task_description,
                device_id,
                platform,
                max_steps,
                mode,
                save_task,
            )
        
        return task_id
    
    async def _execute_natural_language_task_bg(
        self,
        task_id: str,
        task_description: str,
        device_id: Optional[str],
        platform: Optional[str],
        max_steps: int,
        mode: str,
        save_task: bool = True,
    ):
        """Background execution of natural language task using PhoneAgent (VLM-based)."""
        from app.api.v1.websocket import manager as ws_manager
        
        try:
            from app.core.agent.phone_agent import PhoneAgent, AgentConfig
            from app.core.adapters.factory import DeviceAdapterFactory
            from app.core.adapters.base import Platform as AdapterPlatform
            
            if save_task:
                await self._log(task_id, "INFO", "Initializing PhoneAgent (VLM-based)")
            
            platform_enum_map = {
                "android": AdapterPlatform.ANDROID,
                "ios": AdapterPlatform.IOS,
                "harmonyos": AdapterPlatform.HARMONYOS,
            }
            adapter_platform = platform_enum_map.get(platform or "android", AdapterPlatform.ANDROID)
            
            # Create device adapter
            device_kwargs = {}
            if device_id:
                device_kwargs["device_id"] = device_id
            device_adapter = DeviceAdapterFactory.create_adapter(adapter_platform, **device_kwargs)
            
            # Load model config from DB
            from app.services.model_config_service import ModelConfigService
            from app.core.model.client import ModelConfig as PhoneModelConfig
            model_svc = ModelConfigService()
            db_config = await model_svc.get_default_config()
            
            model_config = None
            if db_config:
                model_config = PhoneModelConfig(
                    base_url=db_config.base_url or "",
                    model_name=db_config.model_name,
                    api_key=db_config.api_key,
                )
                if save_task:
                    await self._log(task_id, "INFO", f"Loaded model config: {db_config.name} ({db_config.model_name})")
            else:
                if save_task:
                    await self._log(task_id, "WARNING", "No model config in DB, using defaults (may fail)")
            
            # Create PhoneAgent instance with VLM mode
            agent_config = AgentConfig(
                max_steps=max_steps,
                device_id=device_id,
                lang="cn",
                format="pseudo",  # Use pseudo format for AutoPhone models
                verbose=True,
            )
            
            execution_history = []
            step_count = 0
            log_queue = []
            
            async def async_step_callback(step_info):
                nonlocal step_count
                
                event_type = step_info.get("event", "act")
                action = step_info.get("action", "") or step_info.get("proposed_action", "")
                thinking = step_info.get("thinking", "")
                message = step_info.get("message", "")
                success = step_info.get("success", True)
                full_response = step_info.get("full_response", "")
                
                # For think event, don't increment step count
                if event_type != "think":
                    step_count += 1
                
                # Queue for async processing
                if save_task:
                    if event_type == "think":
                        log_queue.append((task_id, "INFO", f"[Step {step_count}] 思考: {thinking}"))
                        log_queue.append((task_id, "INFO", f"[Step {step_count}] 完整思考过程: {full_response}"))
                    else:
                        log_queue.append((task_id, "INFO", f"[Step {step_count}] {action}: {message or '执行中'}"))
                
                # Send real-time WebSocket update
                ws_data = {
                    "task_id": task_id,
                    "event": event_type,
                    "step": step_count,
                    "action": action,
                    "result": message,
                    "success": success,
                    "thought": thinking,
                    "full_response": full_response,
                }
                try:
                    await ws_manager.send_task_update(task_id, ws_data)
                except Exception as ws_e:
                    if save_task:
                        await self._log(task_id, "WARNING", f"Failed to send WebSocket update: {ws_e}")
                
                # Only add to execution history for action events
                if event_type != "think":
                    execution_history.append({
                        "step": step_count,
                        "action": action,
                        "thinking": thinking,
                        "message": message,
                        "success": success,
                    })
            
            # Get the current event loop for thread-safe callback
            loop = asyncio.get_running_loop()
            
            def step_callback(step_info):
                # Run async callback in main event loop from background thread
                asyncio.run_coroutine_threadsafe(async_step_callback(step_info), loop)
            
            # Create PhoneAgent with callback
            phone_agent = PhoneAgent(
                device=device_adapter,
                model_config=model_config,
                agent_config=agent_config,
                step_callback=step_callback,
            )
            
            if save_task:
                await self._log(task_id, "INFO", f"PhoneAgent initialized, starting execution")
                await self._log(task_id, "INFO", f"Task: {task_description}")
            
            # Execute task using PhoneAgent's run method in a separate thread
            # to avoid blocking the event loop (which would stop video streaming)
            result_message = await asyncio.to_thread(phone_agent.run, task_description)
            
            # Process queued async operations after synchronous run completes
            for log_args in log_queue:
                await self._log(*log_args)
            
            # Send completion message
            completion_data = {
                "event": "completed",
                "step": step_count,
                "success": True,
                "result": result_message,
            }
            await ws_manager.send_task_update(task_id, completion_data)
            
            if save_task:
                import json
                history_path = f"replays/replay_task_{task_id.replace('task_', '')}_{int(time.time())}.json"
                os.makedirs("replays", exist_ok=True)
                with open(history_path, 'w', encoding='utf-8') as f:
                    json.dump(execution_history, f, ensure_ascii=False, indent=2)
                
                await self._log(task_id, "INFO", f"任务执行完成，共执行 {step_count} 步")
                await self._update_task_status(task_id, TaskStatus.COMPLETED, progress=100)
                await self._generate_report(task_id, "", "")
            
        except Exception as e:
            full_tb = traceback.format_exc()
            if save_task:
                await self._log(task_id, "ERROR", f"自然语言任务执行失败: {str(e)}\n{full_tb}")
                self.task_errors[task_id] = str(e)
                await self._update_task_status(task_id, TaskStatus.FAILED, progress=100)
            else:
                print(f"Agent execution failed: {str(e)}\n{full_tb}")
            
            # 发送 WebSocket 失败消息
            error_data = {
                "event": "error",
                "step": 0,
                "success": False,
                "result": f"执行失败: {str(e)}",
            }
            await ws_manager.send_task_update(task_id, error_data)
