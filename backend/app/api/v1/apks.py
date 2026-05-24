"""APK management API."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from app.schemas.apk import ApkInfo, ApkUploadResponse, ApkInstallRequest, ApkActionResponse, ApkBatchDeleteRequest
from app.services.apk_service import ApkService

router = APIRouter()
apk_service = ApkService()


@router.get("/")
async def list_apks():
    apks = await apk_service.list_apks()
    return {"apks": apks}


@router.get("/{apk_id}", response_model=ApkInfo)
async def get_apk(apk_id: str):
    apk = await apk_service.get_apk(apk_id)
    if not apk:
        raise HTTPException(status_code=404, detail="APK not found")
    return apk


@router.post("/upload")
async def upload_apk(file: UploadFile = File(...)):
    result = await apk_service.upload_apk(file, file.filename or "unknown.apk")
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.delete("/{apk_id}")
async def delete_apk(apk_id: str):
    result = await apk_service.delete_apk(apk_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/batch-delete")
async def batch_delete_apks(request: ApkBatchDeleteRequest):
    result = await apk_service.delete_apk_batch(request.apk_ids)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/install")
async def install_apk(request: ApkInstallRequest):
    result = await apk_service.install_apk(request.device_id, request.apk_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result
