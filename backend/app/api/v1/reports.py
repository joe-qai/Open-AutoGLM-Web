"""Report generation API."""

from fastapi import APIRouter, HTTPException, Response
from app.schemas.report import BatchDeleteRequest, BatchDeleteResponse
from app.services.report_service import ReportService

router = APIRouter()
report_service = ReportService()


@router.get("/")
async def list_reports(
    task_id: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    return await report_service.list_reports(task_id, status, skip, limit)


@router.delete("/batch", response_model=BatchDeleteResponse)
async def batch_delete_reports(request: BatchDeleteRequest):
    deleted, failed = await report_service.batch_delete(request.report_ids)
    return BatchDeleteResponse(deleted_count=deleted, failed_ids=failed)


@router.get("/{task_id}")
async def get_report(task_id: str):
    report = await report_service.get_report(task_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{task_id}/preview")
async def preview_report(task_id: str):
    html = await report_service.get_report_html(task_id)
    if not html:
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(content=html, media_type="text/html")


@router.delete("/{task_id}")
async def delete_report(task_id: str):
    await report_service.delete_report(task_id)
    return {"message": "Report deleted successfully"}
