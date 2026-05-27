"""Tests for AuditLogService."""

import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from app.services.audit_log_service import AuditLogService, DB_PATH


class TestAuditLogService:
    """Verify audit log service functionality."""

    def test_log_entry(self):
        """Should log an entry successfully."""
        service = AuditLogService()
        log_id = service.log(
            level="info",
            category="device",
            action="connected",
            operator="user1",
            target_id="device1",
            target_name="Test Device",
            detail={"key": "value"},
            device_id="device1",
        )
        
        assert log_id is not None
        assert log_id.startswith("log_")

    def test_log_entry_with_minimal_params(self):
        """Should log an entry with minimal parameters."""
        service = AuditLogService()
        log_id = service.log(
            action="test_action",
            operator="system",
        )
        
        assert log_id is not None

    def test_list_logs_empty(self):
        """Should return empty list when no logs match."""
        service = AuditLogService()
        logs = service.list_logs(category="nonexistent")
        
        assert isinstance(logs, list)

    def test_list_logs_with_filters(self):
        """Should filter logs by category."""
        service = AuditLogService()
        
        # First add a log
        service.log(
            level="error",
            category="task",
            action="failed",
            operator="user1",
            task_id="task123",
        )
        
        logs = service.list_logs(category="task")
        
        assert isinstance(logs, list)

    def test_get_summary(self):
        """Should return log summary statistics."""
        service = AuditLogService()
        summary = service.get_summary()
        
        assert "total" in summary
        assert "error_count" in summary
        assert "warning_count" in summary
        assert "info_count" in summary
        assert "debug_count" in summary

    def test_clear_logs(self):
        """Should clear all logs."""
        service = AuditLogService()
        
        # Add some logs first
        service.log(action="test1")
        service.log(action="test2")
        
        # Clear logs
        service.clear_logs()
        
        # Verify cleared
        summary = service.get_summary()
        assert summary["total"] == 0

    def test_singleton_pattern(self):
        """Should return the same instance each time."""
        service1 = AuditLogService()
        service2 = AuditLogService()
        
        assert service1 is service2