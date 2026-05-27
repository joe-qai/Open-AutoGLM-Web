"""Base executor class for all execution engines."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExecutorLog:
    """Single log entry from executor."""
    timestamp: datetime = field(default_factory=datetime.now)
    level: str = "INFO"
    message: str = ""


@dataclass
class ExecutorResult:
    """Result of executor execution."""
    status: str  # success, failed, cancelled
    logs: List[ExecutorLog] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration_ms: int = 0
    error_message: Optional[str] = None


class BaseExecutor(ABC):
    """Abstract base class for all executors."""
    
    def __init__(self):
        self.logs: List[ExecutorLog] = []
    
    @abstractmethod
    def start(
        self,
        script: Any,
        device: Any,
        project: Any,
        **kwargs
    ) -> Any:
        """Start execution without blocking."""
        pass
    
    @abstractmethod
    def wait(
        self,
        cancel_check: Optional[callable] = None
    ) -> ExecutorResult:
        """Wait for execution to complete."""
        pass
    
    def _log(self, message: str, level: str = "INFO"):
        """Add log entry."""
        self.logs.append(ExecutorLog(
            timestamp=datetime.now(),
            level=level,
            message=message
        ))
    
    def get_logs(self) -> List[ExecutorLog]:
        """Get all logs."""
        return self.logs
    
    def clear_logs(self):
        """Clear all logs."""
        self.logs.clear()
