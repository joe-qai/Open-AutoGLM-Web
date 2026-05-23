"""Task schemas."""

from pydantic import BaseModel
from enum import Enum
from typing import Optional, List, Dict


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskType(str, Enum):
    """Task type classification."""
    COMPATIBILITY = "compatibility"
    FUNCTIONAL = "functional"
    CRASH = "crash"
    PERFORMANCE = "performance"


class TaskCreate(BaseModel):
    """Request model for creating a task."""
    name: str
    task_type: Optional[TaskType] = None
    platform: Optional[str] = None
    devices: Optional[List[str]] = None
    steps: Optional[List[Dict]] = None
    description: Optional[str] = None
    timeout: Optional[int] = 300
    script_id: Optional[str] = None
    device_id: Optional[str] = None
    apk_id: Optional[str] = None


class TaskUpdate(BaseModel):
    """Request model for updating a task."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None


class TaskResponse(BaseModel):
    """Response model for task information."""
    task_id: str
    name: str
    task_type: TaskType
    platform: str
    devices: List[str]
    status: TaskStatus
    steps: Optional[List[Dict]] = None
    description: Optional[str] = None
    script_id: Optional[str] = None
    device_id: Optional[str] = None
    apk_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    model_config = {"from_attributes": True}


class TaskLog(BaseModel):
    """Task log entry."""
    timestamp: str
    level: str
    message: str
    step: Optional[int] = None


class BatchDeleteTasksRequest(BaseModel):
    """Request model for batch deleting tasks."""
    task_ids: List[str]


class BatchDeleteTasksResponse(BaseModel):
    """Response model for batch deleting tasks."""
    deleted_count: int
    failed_ids: List[str] = []
