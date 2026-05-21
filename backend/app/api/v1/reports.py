"""Report generation API."""

from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.report import ReportInfo, ReportStatus, ReportType, BatchDeleteRequest, BatchDeleteResponse
from app.services.report_service import ReportService

router = APIRouter()
report_service = ReportService()


@router.get("/", response_model=List[ReportInfo])
async def list_reports(
    task_id: str | None = None,
    status: ReportStatus | None = None,
    report_type: ReportType | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all reports."""
    return report_service.list_reports(task_id, status, report_type, skip, limit)


@router.delete("/batch", response_model=BatchDeleteResponse)
async def batch_delete_reports(request: BatchDeleteRequest):
    """Batch delete multiple reports."""
    deleted, failed = report_service.batch_delete(request.report_ids)
    return BatchDeleteResponse(deleted_count=deleted, failed_ids=failed)


@router.get("/{report_id}", response_model=ReportInfo)
async def get_report(report_id: str):
    """Get report details."""
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/generate")
async def generate_report(report_id: str):
    """Generate a report for a task."""
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    result = report_service.generate_report(report_id)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to generate report")
    return {"status": "generated", "report_id": report_id}


@router.get("/{report_id}/download")
async def download_report(report_id: str, format: str = "html"):
    """Download report in specified format."""
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    content = report_service.download_report(report_id, format)
    if not content:
        raise HTTPException(status_code=400, detail="Failed to download report")
    
    return {"content": content, "format": format}


@router.delete("/{report_id}")
async def delete_report(report_id: str):
    """Delete a report."""
    report = report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report_service.delete_report(report_id)
    return {"message": "Report deleted successfully"}
