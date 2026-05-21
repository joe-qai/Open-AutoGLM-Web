"""Updated log schemas with category/action/operator fields."""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class LogCategory(str, Enum):
    DEVICE = "device"
    SCRIPT = "script"
    TASK = "task"
    AGENT = "agent"
    SYSTEM = "system"
    API = "api"


class LogEntry(BaseModel):
    log_id: str
    level: LogLevel
    category: LogCategory
    action: str
    operator: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    detail: Optional[dict[str, Any]] = None
    device_id: Optional[str] = None
    script_id: Optional[str] = None
    task_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class LogSummary(BaseModel):
    total: int
    error_count: int
    warning_count: int
    info_count: int
    debug_count: int
    avg_response_time_ms: Optional[float] = None