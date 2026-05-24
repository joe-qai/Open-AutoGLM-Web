"""APK management schemas."""

from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Optional
from datetime import datetime


class ApkStatus(str, Enum):
    """APK status."""
    UPLOADED = "uploaded"
    INSTALLED = "installed"
    FAILED = "failed"


class ApkInfo(BaseModel):
    """APK information model."""
    id: str
    name: str
    original_filename: Optional[str] = None
    version: Optional[str] = None
    package_name: Optional[str] = None
    file_size: Optional[int] = None
    upload_time: datetime
    status: ApkStatus
    file_path: Optional[str] = None

    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ApkUploadResponse(BaseModel):
    """Response for APK upload."""
    success: bool
    message: str
    apk: Optional[ApkInfo] = None


class ApkInstallRequest(BaseModel):
    """Request for installing APK."""
    device_id: str
    apk_id: str


class ApkActionResponse(BaseModel):
    """Response for APK actions."""
    success: bool
    message: str


class ApkBatchDeleteRequest(BaseModel):
    """Request for batch deleting APKs."""
    apk_ids: list[str]
