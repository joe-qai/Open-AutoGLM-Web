"""Report service for generating and managing reports."""

from typing import List, Optional
import time
import json

from app.schemas.report import ReportInfo, ReportStatus, ReportType, IssueDetail, IssueSeverity, IssueCategory


class ReportService:
    """Service for report management."""
    
    def __init__(self):
        self.reports = {}
        # 添加一些模拟数据供测试
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample reports for testing."""
        sample_reports = [
            {
                "report_id": "report_1",
                "name": "测试报告-微信自动化",
                "task_id": "task_001",
                "task_name": "微信登录测试",
                "platform": "android",
                "status": "completed",
                "report_type": "html",
                "duration": 120,
                "issues": [
                    {
                        "issue_id": "issue_001",
                        "severity": "high",
                        "category": "ui_compatibility",
                        "title": "按钮对齐问题",
                        "description": "在小屏幕上按钮未正确对齐",
                        "suggestion": "使用响应式布局约束"
                    },
                    {
                        "issue_id": "issue_002",
                        "severity": "medium",
                        "category": "functional_error",
                        "title": "输入验证缺失",
                        "description": "表单接受无效邮箱格式",
                        "suggestion": "添加邮箱验证正则表达式"
                    }
                ],
                "summary": {
                    "total_issues": 2,
                    "critical_count": 0,
                    "high_count": 1,
                    "medium_count": 1,
                    "low_count": 0
                },
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:32:00",
                "generated_at": "2024-01-15T10:32:00"
            },
            {
                "report_id": "report_2",
                "name": "测试报告-小红书搜索",
                "task_id": "task_002",
                "task_name": "小红书搜索功能测试",
                "platform": "ios",
                "status": "completed",
                "report_type": "html",
                "duration": 180,
                "issues": [],
                "summary": {
                    "total_issues": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0
                },
                "created_at": "2024-01-14T15:20:00",
                "updated_at": "2024-01-14T15:23:00",
                "generated_at": "2024-01-14T15:23:00"
            },
            {
                "report_id": "report_3",
                "name": "测试报告-支付宝支付",
                "task_id": "task_003",
                "task_name": "支付宝支付流程测试",
                "platform": "harmonyos",
                "status": "running",
                "report_type": "html",
                "duration": None,
                "issues": [],
                "summary": None,
                "created_at": "2024-01-16T09:00:00",
                "updated_at": None,
                "generated_at": None
            },
            {
                "report_id": "report_4",
                "name": "测试报告-抖音短视频",
                "task_id": "task_004",
                "task_name": "抖音视频播放测试",
                "platform": "android",
                "status": "failed",
                "report_type": "html",
                "duration": 45,
                "issues": [
                    {
                        "issue_id": "issue_003",
                        "severity": "critical",
                        "category": "crash",
                        "title": "应用崩溃",
                        "description": "视频播放时应用意外崩溃",
                        "suggestion": "检查视频解码逻辑"
                    }
                ],
                "summary": {
                    "total_issues": 1,
                    "critical_count": 1,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0
                },
                "created_at": "2024-01-13T14:45:00",
                "updated_at": "2024-01-13T14:45:45",
                "generated_at": "2024-01-13T14:45:45"
            }
        ]
        
        for report_data in sample_reports:
            self.reports[report_data["report_id"]] = report_data
    
    def list_reports(
        self,
        task_id: str | None = None,
        status: ReportStatus | None = None,
        report_type: ReportType | None = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ReportInfo]:
        """List all reports."""
        report_list = []
        
        for report_data in self.reports.values():
            if task_id and report_data["task_id"] != task_id:
                continue
            if status and report_data["status"] != status.value:
                continue
            if report_type and report_data["report_type"] != report_type.value:
                continue
            
            issues = []
            for issue_data in report_data.get("issues", []):
                issues.append(IssueDetail(
                    issue_id=issue_data["issue_id"],
                    severity=IssueSeverity(issue_data["severity"]),
                    category=IssueCategory(issue_data["category"]),
                    title=issue_data["title"],
                    description=issue_data["description"],
                    screenshot_path=issue_data.get("screenshot_path"),
                    device_info=issue_data.get("device_info"),
                    suggestion=issue_data.get("suggestion")
                ))
            
            report_list.append(ReportInfo(
                report_id=report_data["report_id"],
                name=report_data["name"],
                task_id=report_data["task_id"],
                task_name=report_data["task_name"],
                platform=report_data["platform"],
                status=ReportStatus(report_data["status"]),
                report_type=ReportType(report_data["report_type"]),
                duration=report_data.get("duration"),
                issues=issues,
                summary=report_data.get("summary"),
                created_at=report_data["created_at"],
                updated_at=report_data.get("updated_at"),
                generated_at=report_data.get("generated_at")
            ))
        
        return report_list[skip:skip + limit]
    
    def get_report(self, report_id: str) -> Optional[ReportInfo]:
        """Get report by ID."""
        report_data = self.reports.get(report_id)
        if not report_data:
            return None
        
        issues = []
        for issue_data in report_data.get("issues", []):
            issues.append(IssueDetail(
                issue_id=issue_data["issue_id"],
                severity=IssueSeverity(issue_data["severity"]),
                category=IssueCategory(issue_data["category"]),
                title=issue_data["title"],
                description=issue_data["description"],
                screenshot_path=issue_data.get("screenshot_path"),
                device_info=issue_data.get("device_info"),
                suggestion=issue_data.get("suggestion")
            ))
        
        return ReportInfo(
            report_id=report_data["report_id"],
            name=report_data["name"],
            task_id=report_data["task_id"],
            task_name=report_data["task_name"],
            platform=report_data["platform"],
            status=ReportStatus(report_data["status"]),
            report_type=ReportType(report_data["report_type"]),
            duration=report_data.get("duration"),
            issues=issues,
            summary=report_data.get("summary"),
            created_at=report_data["created_at"],
            updated_at=report_data.get("updated_at"),
            generated_at=report_data.get("generated_at")
        )
    
    def generate_report(self, report_id: str) -> bool:
        """Generate a report."""
        report_data = self.reports.get(report_id)
        if not report_data:
            return False
        
        report_data["status"] = ReportStatus.GENERATING.value
        
        time.sleep(1)
        
        report_data["issues"] = [
            {
                "issue_id": f"issue_{int(time.time())}",
                "severity": "high",
                "category": "ui_compatibility",
                "title": "Button alignment issue",
                "description": "Button is not properly aligned on smaller screens",
                "suggestion": "Use responsive layout constraints"
            },
            {
                "issue_id": f"issue_{int(time.time()) + 1}",
                "severity": "medium",
                "category": "functional_error",
                "title": "Input validation missing",
                "description": "Form accepts invalid email format",
                "suggestion": "Add email validation regex"
            }
        ]
        
        report_data["summary"] = {
            "total_issues": 2,
            "critical_count": 0,
            "high_count": 1,
            "medium_count": 1,
            "low_count": 0
        }
        
        report_data["status"] = ReportStatus.COMPLETED.value
        report_data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        report_data["updated_at"] = report_data["generated_at"]
        
        return True
    
    def download_report(self, report_id: str, format: str = "html") -> Optional[str]:
        """Download report in specified format."""
        report = self.get_report(report_id)
        if not report:
            return None
        
        if format == "json":
            return json.dumps({
                "report_id": report.report_id,
                "task_id": report.task_id,
                "status": report.status.value,
                "issues": [issue.__dict__ for issue in report.issues],
                "summary": report.summary
            }, indent=2)
        
        elif format == "html":
            issues_html = ""
            for issue in report.issues:
                issues_html += f"""
                <div class="issue {issue.severity.value}">
                    <h3>{issue.title}</h3>
                    <p>{issue.description}</p>
                    <p><strong>Suggestion:</strong> {issue.suggestion}</p>
                </div>
                """
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Report</title>
                <style>
                    .issue {{ padding: 10px; margin: 10px; border-radius: 5px; }}
                    .critical {{ background-color: #ffcccc; }}
                    .high {{ background-color: #ffebcc; }}
                    .medium {{ background-color: #ffffcc; }}
                    .low {{ background-color: #ccffcc; }}
                </style>
            </head>
            <body>
                <h1>Test Report</h1>
                <p>Report ID: {report.report_id}</p>
                <p>Task ID: {report.task_id}</p>
                <h2>Issues Found:</h2>
                {issues_html}
            </body>
            </html>
            """
        
        return None
    
    def delete_report(self, report_id: str):
        """Delete a report."""
        if report_id in self.reports:
            del self.reports[report_id]
    
    def create_report(self, task_id: str, task_name: str, platform: str) -> str:
        """Create a new report."""
        report_id = f"report_{int(time.time())}"
        
        self.reports[report_id] = {
            "report_id": report_id,
            "name": f"测试报告-{task_name}",
            "task_id": task_id,
            "task_name": task_name,
            "platform": platform,
            "status": ReportStatus.PENDING.value,
            "report_type": "html",
            "duration": None,
            "issues": [],
            "summary": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": None,
            "generated_at": None
        }
        
        return report_id

    def batch_delete(self, report_ids: list[str]) -> tuple[int, list[str]]:
        """Batch delete reports. Returns (deleted_count, failed_ids)."""
        deleted = 0
        failed = []
        for report_id in report_ids:
            if report_id in self.reports:
                del self.reports[report_id]
                deleted += 1
            else:
                failed.append(report_id)
        return deleted, failed