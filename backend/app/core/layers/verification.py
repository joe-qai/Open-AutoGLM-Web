"""Verification layer for the Agent architecture."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class VerificationStatus(str, Enum):
    """Verification result status."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class VerificationIssue:
    """Issue found during verification."""
    id: str
    severity: IssueSeverity
    title: str
    description: str
    screenshot_path: Optional[str] = None
    suggestion: Optional[str] = None
    device_info: Optional[str] = None


@dataclass
class VerificationResult:
    """Result of verification."""
    status: VerificationStatus
    issues: List[VerificationIssue] = field(default_factory=list)
    message: str = ""
    metrics: Optional[Dict[str, Any]] = None


class VerificationLayer:
    """Verification layer - validates task execution results."""
    
    def __init__(self):
        self.issue_id_counter = 0
    
    def verify(self, task_description: str, execution_history: List[Dict]) -> VerificationResult:
        """Verify task execution results."""
        issues = []
        
        # Check for crashes
        crash_issues = self._check_for_crashes(execution_history)
        issues.extend(crash_issues)
        
        # Check for UI anomalies
        ui_issues = self._check_ui_anomalies(execution_history)
        issues.extend(ui_issues)
        
        # Check for task completion
        completion_issues = self._check_task_completion(task_description, execution_history)
        issues.extend(completion_issues)
        
        # Determine overall status
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        if critical_issues:
            status = VerificationStatus.FAILED
            message = f"Verification failed with {len(critical_issues)} critical issues"
        elif issues:
            status = VerificationStatus.WARNING
            message = f"Verification passed with {len(issues)} warnings"
        else:
            status = VerificationStatus.PASSED
            message = "Verification passed"
        
        return VerificationResult(
            status=status,
            issues=issues,
            message=message,
            metrics={
                "total_issues": len(issues),
                "critical_count": len(critical_issues),
                "execution_steps": len(execution_history)
            }
        )
    
    def _check_for_crashes(self, history: List[Dict]) -> List[VerificationIssue]:
        """Check execution history for crash indicators."""
        issues = []
        
        for step in history:
            if "crash" in str(step.get("action", "")).lower():
                issues.append(VerificationIssue(
                    id=self._generate_id(),
                    severity=IssueSeverity.CRITICAL,
                    title="Application Crash",
                    description="Application crashed during execution",
                    suggestion="Check application logs for crash details"
                ))
        
        return issues
    
    def _check_ui_anomalies(self, history: List[Dict]) -> List[VerificationIssue]:
        """Check for UI-related anomalies."""
        issues = []
        
        # Look for repeated failed actions
        action_counts = {}
        for step in history:
            action = step.get("action", "")
            action_counts[action] = action_counts.get(action, 0) + 1
        
        for action, count in action_counts.items():
            if count > 5 and action in ["tap_element", "swipe"]:
                issues.append(VerificationIssue(
                    id=self._generate_id(),
                    severity=IssueSeverity.MEDIUM,
                    title=f"Repeated Action: {action}",
                    description=f"Action '{action}' was performed {count} times",
                    suggestion="Check if element is properly identified or accessible"
                ))
        
        return issues
    
    def _check_task_completion(self, task_description: str, history: List[Dict]) -> List[VerificationIssue]:
        """Check if task was completed."""
        issues = []
        
        # Check if finish action was called
        finished = any(step.get("action") == "finish" for step in history)
        
        if not finished:
            issues.append(VerificationIssue(
                id=self._generate_id(),
                severity=IssueSeverity.HIGH,
                title="Task Not Completed",
                description="Task did not reach completion",
                suggestion="Check if task description is clear or if execution was interrupted"
            ))
        
        return issues
    
    def _generate_id(self) -> str:
        """Generate unique issue ID."""
        self.issue_id_counter += 1
        return f"issue_{self.issue_id_counter:04d}"
    
    def generate_report(self, result: VerificationResult) -> str:
        """Generate human-readable report."""
        report_lines = [
            "=" * 60,
            "VERIFICATION REPORT",
            "=" * 60,
            f"Status: {result.status.value}",
            f"Message: {result.message}",
            "",
            "ISSUES FOUND:",
            "-" * 60
        ]
        
        for issue in result.issues:
            report_lines.extend([
                f"[{issue.severity.value.upper()}] {issue.title}",
                f"  ID: {issue.id}",
                f"  Description: {issue.description}",
                f"  Suggestion: {issue.suggestion or 'None'}",
                ""
            ])
        
        if result.metrics:
            report_lines.extend([
                "-" * 60,
                "METRICS:",
                "-" * 60
            ])
            for key, value in result.metrics.items():
                report_lines.append(f"  {key}: {value}")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
