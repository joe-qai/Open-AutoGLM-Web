"""Log service backed by SQLite audit log."""

from typing import List, Optional

from app.services.audit_log_service import AuditLogService
from app.schemas.log import LogEntry, LogLevel, LogCategory, LogSummary


class LogService:
    """Service for managing log entries, backed by AuditLogService (SQLite)."""

    def __init__(self):
        self.audit = AuditLogService()

    def create_log(
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
        """Create a new log entry via the audit log service."""
        return self.audit.log(
            level=level,
            category=category,
            action=action,
            operator=operator,
            target_id=target_id,
            target_name=target_name,
            detail=detail,
            device_id=device_id,
            script_id=script_id,
            task_id=task_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            error=error,
        )

    @staticmethod
    def _map_to_entry(log_dict: dict) -> LogEntry:
        """Map SQLite row dict (timestamp) to LogEntry schema (created_at)."""
        mapped = {**log_dict}
        if "timestamp" in mapped and "created_at" not in mapped:
            mapped["created_at"] = mapped.pop("timestamp")
        return LogEntry(**mapped)

    def get_log(self, log_id: str) -> Optional[LogEntry]:
        """Get log by ID."""
        logs = self.audit.list_logs(limit=1)
        for log_dict in logs:
            if log_dict.get("log_id") == log_id:
                return self._map_to_entry(log_dict)
        return None

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
    ) -> List[LogEntry]:
        """List logs with filters."""
        log_dicts = self.audit.list_logs(
            level=level,
            category=category,
            device_id=device_id,
            script_id=script_id,
            task_id=task_id,
            search=search,
            start_time=start_time,
            end_time=end_time,
            skip=skip,
            limit=min(limit, 500),
        )
        return [self._map_to_entry(d) for d in log_dicts]

    def get_summary(self) -> LogSummary:
        """Get log summary statistics."""
        summary_dict = self.audit.get_summary()
        return LogSummary(**summary_dict)

    def clear_logs(self):
        """Clear all logs."""
        self.audit.clear_logs()

    # Convenience methods
    def log_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: int, error: Optional[str] = None):
        """Log an API request."""
        level = "error" if status_code >= 400 else "info"
        action = "failed" if status_code >= 400 else "success"
        self.create_log(
            level=level, category="api", action=action, operator="system",
            endpoint=endpoint, method=method, status_code=status_code,
            duration_ms=duration_ms, error=error,
        )

    def log_script_execution(self, script_id: str, action: str = "executed", device_id: Optional[str] = None, error: Optional[str] = None):
        """Log script execution."""
        level = "error" if error else "info"
        self.create_log(
            level=level, category="script", action=action, operator="user",
            target_id=script_id, device_id=device_id, error=error,
        )

    def log_task_execution(self, task_id: str, action: str = "executed", script_id: Optional[str] = None, error: Optional[str] = None):
        """Log task execution."""
        level = "error" if error else "info"
        self.create_log(
            level=level, category="task", action=action, operator="system",
            target_id=task_id, script_id=script_id, error=error,
        )

    def log_device_operation(self, device_id: str, action: str = "connected", success: bool = True, error: Optional[str] = None):
        """Log device operation."""
        level = "error" if not success else "info"
        self.create_log(
            level=level, category="device", action=action, operator="system",
            target_id=device_id, device_id=device_id, error=error,
        )

    def log_system(self, message: str, level: str = "info", detail: Optional[dict] = None):
        """Log system message."""
        self.create_log(
            level=level, category="system", action="event", operator="system",
            detail={"message": message} if not detail else {**detail, "message": message},
        )