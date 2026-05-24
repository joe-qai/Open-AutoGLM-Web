"""Report schemas."""

from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Optional, List, Dict


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportType(str, Enum):
    """Report type classification."""
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, Enum):
    """Issue categories."""
    UI_COMPATIBILITY = "ui_compatibility"
    CRASH = "crash"
    FUNCTIONAL_ERROR = "functional_error"
    PERFORMANCE = "performance"
    SECURITY = "security"


class IssueDetail(BaseModel):
    """Issue detail model."""
    issue_id: str
    severity: IssueSeverity
    category: IssueCategory
    title: str
    description: str
    screenshot_path: Optional[str] = None
    device_info: Optional[str] = None
    suggestion: Optional[str] = None


class ReportInfo(BaseModel):
    """Report information model."""
    report_id: str
    name: str
    task_id: str
    task_name: str
    platform: str
    status: ReportStatus
    report_type: ReportType
    duration: Optional[int] = None
    issues: Optional[List[IssueDetail]] = None
    summary: Optional[Dict] = None
    created_at: str
    updated_at: Optional[str] = None
    generated_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class BatchDeleteRequest(BaseModel):
    """Request model for batch deleting reports."""
    report_ids: List[str]


class BatchDeleteResponse(BaseModel):
    """Response model for batch deleting reports."""
    deleted_count: int
    failed_ids: List[str] = []