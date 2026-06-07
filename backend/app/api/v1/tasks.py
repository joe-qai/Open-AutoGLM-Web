"""Task management API."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
from app.schemas.task import TaskResponse, TaskStatus, TaskCreate, BatchDeleteTasksRequest, BatchDeleteTasksResponse
from app.services.task_service import TaskService

router = APIRouter()
task_service = TaskService()


class NaturalLanguageTaskRequest(BaseModel):
    """Request to execute a task via natural language."""
    task_description: str
    device_id: Optional[str] = None
    platform: Optional[str] = "android"
    max_steps: Optional[int] = 100
    mode: Optional[str] = "llm"  # "llm", "vlm", or "auto"
    save_task: Optional[bool] = True  # Whether to save task record


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate):
    task_id = await task_service.create_task(
        name=task.name,
        task_type=task.task_type,
        platform=task.platform,
        devices=task.devices,
        steps=task.steps,
        description=task.description,
        script_id=task.script_id,
        device_id=task.device_id,
        apk_id=task.apk_id,
        model_config_id=task.model_config_id,
    )
    return await task_service.get_task(task_id)


@router.post("/{task_id}/execute")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == TaskStatus.EXECUTING:
        raise HTTPException(status_code=400, detail="Task is already running")
    background_tasks.add_task(task_service.execute_task, task_id)
    return {"task_id": task_id, "status": "executing"}


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await task_service.stop_task(task_id)
    return {"task_id": task_id, "status": "stopped"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    tasks = await task_service.list_tasks(status, platform, skip, limit)
    return {"tasks": tasks}


@router.delete("/batch", response_model=BatchDeleteTasksResponse)
async def batch_delete_tasks(request: BatchDeleteTasksRequest):
    deleted, failed = await task_service.batch_delete(request.task_ids)
    return BatchDeleteTasksResponse(deleted_count=deleted, failed_ids=failed)


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await task_service.delete_task(task_id)
    return {"message": "Task deleted successfully"}


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str, limit: int = 100):
    logs = await task_service.get_task_logs(task_id, limit)
    return {"logs": logs}


@router.post("/natural-language")
async def execute_natural_language_task(request: NaturalLanguageTaskRequest, background_tasks: BackgroundTasks):
    """Execute a task using natural language."""
    task_id = await task_service.execute_natural_language_task(
        task_description=request.task_description,
        device_id=request.device_id,
        platform=request.platform,
        max_steps=request.max_steps,
        mode=request.mode,
        save_task=request.save_task,
        background_tasks=background_tasks,
    )
    return {"task_id": task_id, "status": "executing"}
