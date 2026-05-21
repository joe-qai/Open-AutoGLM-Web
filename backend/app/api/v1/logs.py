"""Log management API — backed by SQLite audit log."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.schemas.log import LogEntry, LogLevel, LogCategory, LogSummary
from app.services.log_service import LogService

router = APIRouter()
log_service = LogService()


@router.get("/", response_model=List[LogEntry])
async def list_logs(
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    script_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
):
    """List all logs with optional filters."""
    return log_service.list_logs(
        level=level,
        category=category,
        device_id=device_id,
        script_id=script_id,
        task_id=task_id,
        search=search,
        start_time=start_time,
        end_time=end_time,
        skip=skip,
        limit=limit,
    )


@router.get("/summary", response_model=LogSummary)
async def get_log_summary():
    """Get log summary statistics."""
    return log_service.get_summary()


@router.delete("/")
async def clear_logs():
    """Clear all logs."""
    log_service.clear_logs()
    return {"message": "All logs cleared successfully"}