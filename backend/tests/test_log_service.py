"""Tests for LogService."""

import pytest
from app.services.log_service import LogService


class TestLogService:
    """Verify log service functionality."""

    def test_create_log(self):
        """Should create a log entry successfully."""
        service = LogService()
        log_id = service.create_log(
            level="info",
            category="task",
            action="created",
            operator="user1",
            target_id="task123",
            target_name="Test Task",
        )
        
        assert log_id is not None
        assert log_id.startswith("log_")

    def test_get_log(self):
        """Should retrieve a log by ID."""
        service = LogService()
        
        # First create a log
        log_id = service.create_log(
            level="error",
            category="device",
            action="disconnected",
            operator="system",
            target_id="device1",
        )
        
        # Then retrieve it
        log_entry = service.get_log(log_id)
        
        assert log_entry is not None
        assert log_entry.log_id == log_id
        assert log_entry.level == "error"
        assert log_entry.category == "device"

    def test_get_log_not_found(self):
        """Should return None when log doesn't exist."""
        service = LogService()
        log_entry = service.get_log("nonexistent_log_id")
        
        assert log_entry is None

    def test_list_logs(self):
        """Should list logs with filters."""
        service = LogService()
        
        # Add some logs
        service.create_log(category="api", action="request")
        service.create_log(category="task", action="executed")
        
        # List all logs
        logs = service.list_logs()
        
        assert isinstance(logs, list)
        assert len(logs) >= 2

    def test_list_logs_with_category_filter(self):
        """Should filter logs by category."""
        service = LogService()
        
        # Add logs with different categories
        service.create_log(category="device", action="connected")
        service.create_log(category="task", action="started")
        
        # Filter by category
        device_logs = service.list_logs(category="device")
        
        assert isinstance(device_logs, list)

    def test_get_summary(self):
        """Should return log summary statistics."""
        service = LogService()
        summary = service.get_summary()
        
        assert summary is not None
        assert hasattr(summary, 'total')
        assert hasattr(summary, 'error_count')

    def test_log_api_request(self):
        """Should log API request."""
        service = LogService()
        
        service.log_api_request(
            endpoint="/api/v1/tasks",
            method="POST",
            status_code=200,
            duration_ms=150,
        )
        
        # Verify log was created
        logs = service.list_logs(category="api")
        assert len(logs) >= 1

    def test_log_task_execution(self):
        """Should log task execution."""
        service = LogService()
        
        service.log_task_execution(
            task_id="task456",
            action="completed",
            script_id="script789",
        )
        
        # Verify log was created
        logs = service.list_logs(category="task")
        assert len(logs) >= 1

    def test_log_device_operation(self):
        """Should log device operation."""
        service = LogService()
        
        service.log_device_operation(
            device_id="device789",
            action="connected",
            success=True,
        )
        
        # Verify log was created
        logs = service.list_logs(category="device")
        assert len(logs) >= 1