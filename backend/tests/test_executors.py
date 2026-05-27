"""Tests for executor module."""

import pytest
import time
from unittest.mock import MagicMock, patch

from app.core.executors.base import BaseExecutor, ExecutorResult, ExecutorLog
from app.core.executors.script_executor import ScriptExecutor
from app.core.executors.task_dispatcher import TaskDispatcher


class TestExecutorLog:
    """Test ExecutorLog dataclass."""
    
    def test_log_creation(self):
        log = ExecutorLog(level="INFO", message="Test message")
        assert log.level == "INFO"
        assert log.message == "Test message"
        assert log.timestamp is not None


class TestExecutorResult:
    """Test ExecutorResult dataclass."""
    
    def test_result_success(self):
        result = ExecutorResult(status="success", exit_code=0)
        assert result.status == "success"
        assert result.exit_code == 0
        assert result.logs == []
    
    def test_result_failed(self):
        result = ExecutorResult(status="failed", exit_code=1, error_message="Test error")
        assert result.status == "failed"
        assert result.exit_code == 1
        assert result.error_message == "Test error"


class TestScriptExecutor:
    """Test ScriptExecutor class."""
    
    def test_simple_script_execution(self):
        """Test executing a simple Python script."""
        executor = ScriptExecutor()
        
        script_content = """
import os
print(f"Device: {os.environ.get('DEVICE_SERIAL', 'N/A')}")
print("Hello from script!")
"""
        
        # Start execution
        executor.start(script_content)
        
        # Wait for completion
        result = executor.wait()
        
        assert result.status == "success"
        assert result.exit_code == 0
        assert "Hello from script!" in result.stdout
        assert "Device: N/A" in result.stdout
    
    def test_script_with_error(self):
        """Test executing a script that fails."""
        executor = ScriptExecutor()
        
        script_content = """
raise ValueError("Test error")
"""
        
        executor.start(script_content)
        result = executor.wait()
        
        assert result.status == "failed"
        assert result.exit_code != 0
    
    def test_script_with_env_vars(self):
        """Test environment variable injection."""
        executor = ScriptExecutor()
        
        script_content = """
import os
print(f"MY_VAR: {os.environ.get('MY_VAR', '')}")
"""
        
        executor.start(script_content, env_vars={"MY_VAR": "test_value"})
        result = executor.wait()
        
        assert result.status == "success"
        assert "MY_VAR: test_value" in result.stdout
    
    def test_script_cancellation(self):
        """Test script cancellation."""
        executor = ScriptExecutor()
        
        script_content = """
import time
for i in range(5):
    print(f"Step {i}")
    time.sleep(0.5)
"""
        
        executor.start(script_content)
        
        # Cancel immediately
        result = executor.wait(cancel_check=lambda: True)
        
        assert result.status == "cancelled"
    
    def test_missing_module_error(self):
        """Test that missing module error is parsed correctly."""
        executor = ScriptExecutor()
        
        script_content = """
import nonexistent_module_xyz123
"""
        
        executor.start(script_content)
        result = executor.wait()
        
        assert result.status == "failed"
        assert "nonexistent_module_xyz123" in result.error_message


class TestTaskDispatcher:
    """Test TaskDispatcher class."""
    
    def test_is_cancelled_initially_false(self):
        """Test that is_cancelled returns False initially."""
        dispatcher = TaskDispatcher()
        assert dispatcher.is_cancelled("test_task") is False
    
    def test_cancel_task_sets_flag(self):
        """Test that cancel_task sets the cancel flag."""
        dispatcher = TaskDispatcher()
        dispatcher.cancel_task("test_task")
        assert dispatcher.is_cancelled("test_task") is True
    
    def test_dispatch_with_no_devices(self):
        """Test dispatch with empty device list."""
        import asyncio
        dispatcher = TaskDispatcher()
        
        async def test():
            results = await dispatcher.dispatch(
                "test_task",
                "print('hello')",
                []
            )
            assert results == {}
        
        asyncio.run(test())
    
    def test_dispatch_with_single_device(self):
        """Test dispatch to a single device."""
        import asyncio
        dispatcher = TaskDispatcher()
        
        # Create mock device
        mock_device = MagicMock()
        mock_device.serial = "test_device_1"
        
        async def test():
            results = await dispatcher.dispatch(
                "test_task",
                "print('hello from device')",
                [mock_device]
            )
            
            assert len(results) == 1
            assert "test_device_1" in results
            assert results["test_device_1"].status == "success"
        
        asyncio.run(test())
    
    def test_dispatch_with_multiple_devices(self):
        """Test dispatch to multiple devices concurrently."""
        import asyncio
        dispatcher = TaskDispatcher()
        
        # Create mock devices
        mock_device_1 = MagicMock()
        mock_device_1.serial = "device_1"
        
        mock_device_2 = MagicMock()
        mock_device_2.serial = "device_2"
        
        async def test():
            results = await dispatcher.dispatch(
                "test_task",
                "import os; print(f'Device: {os.environ.get(\"DEVICE_SERIAL\")}')",
                [mock_device_1, mock_device_2]
            )
            
            assert len(results) == 2
            assert "device_1" in results
            assert "device_2" in results
        
        asyncio.run(test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
