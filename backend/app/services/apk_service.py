"""APK management service."""

import os
import uuid
import subprocess
import re
from typing import List, Optional
from datetime import datetime

from app.schemas.apk import ApkInfo, ApkStatus, ApkUploadResponse, ApkActionResponse
from app.services.apk_metadata_service import ApkMetadataService
from app.config import settings


class ApkService:
    """Service for APK management."""
    
    def __init__(self):
        self.apks = {}
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "apks")
        os.makedirs(self.upload_dir, exist_ok=True)
        self.metadata = ApkMetadataService()
    
    def _parse_apk_info(self, file_path: str) -> dict:
        """Parse APK info using aapt2 (preferred) with aapt fallback."""
        info = {
            "version": None,
            "package_name": None
        }

        # Try aapt2 first (recommended for modern Android SDK)
        try:
            result = subprocess.run(
                ["aapt2", "dump", "badging", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                # Parse package name: aapt2 format is "package: name='xxx' versionCode='N' ..."
                pkg_match = re.search(r"package: name='([^']+)'", result.stdout)
                if pkg_match:
                    info["package_name"] = pkg_match.group(1)

                # Parse version name
                ver_match = re.search(r"versionName='([^']+)'", result.stdout)
                if ver_match:
                    info["version"] = ver_match.group(1)

                return info
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback to aapt if aapt2 is not available
        try:
            result = subprocess.run(
                ["aapt", "dump", "badging", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                pkg_match = re.search(r"package: name='([^']+)'", result.stdout)
                if pkg_match:
                    info["package_name"] = pkg_match.group(1)

                ver_match = re.search(r"versionName='([^']+)'", result.stdout)
                if ver_match:
                    info["version"] = ver_match.group(1)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return info
    
    def list_apks(self) -> List[ApkInfo]:
        """List all uploaded APKs."""
        apk_list = []

        # Check upload directory for APK files
        for filename in os.listdir(self.upload_dir):
            if filename.endswith(".apk"):
                file_path = os.path.join(self.upload_dir, filename)
                file_stat = os.stat(file_path)

                # Generate ID from filename (without extension)
                apk_id = os.path.splitext(filename)[0]

                # Try to parse APK info
                apk_info = self._parse_apk_info(file_path)

                # Query metadata for original_filename
                meta = self.metadata.get(apk_id)
                original_filename = meta.get("original_filename") if meta else filename

                apk_list.append(ApkInfo(
                    id=apk_id,
                    name=filename,
                    original_filename=original_filename,
                    version=apk_info.get("version"),
                    package_name=apk_info.get("package_name"),
                    file_size=file_stat.st_size,
                    upload_time=datetime.fromtimestamp(file_stat.st_mtime),
                    status=ApkStatus.UPLOADED,
                    file_path=file_path
                ))

        return apk_list
    
    def get_apk(self, apk_id: str) -> Optional[ApkInfo]:
        """Get APK by ID."""
        apks = self.list_apks()
        return next((a for a in apks if a.id == apk_id), None)
    
    async def upload_apk(self, file, filename: str) -> ApkUploadResponse:
        """Upload an APK file."""
        try:
            # Generate unique ID
            apk_id = str(uuid.uuid4())[:8]
            original_ext = os.path.splitext(filename)[1]
            if not original_ext:
                original_ext = ".apk"
            saved_filename = f"{apk_id}{original_ext}"
            file_path = os.path.join(self.upload_dir, saved_filename)
            
            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Parse APK info
            apk_info_data = self._parse_apk_info(file_path)

            # Save metadata to SQLite
            self.metadata.save(
                apk_id=apk_id,
                original_filename=filename,
                package_name=apk_info_data.get("package_name"),
                version=apk_info_data.get("version"),
                file_size=len(content),
                upload_time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                status="uploaded"
            )

            # Create APK info object
            apk_info = ApkInfo(
                id=apk_id,
                name=filename,
                original_filename=filename,
                version=apk_info_data.get("version"),
                package_name=apk_info_data.get("package_name"),
                file_size=len(content),
                upload_time=datetime.now(),
                status=ApkStatus.UPLOADED,
                file_path=file_path
            )
            
            return ApkUploadResponse(
                success=True,
                message="APK uploaded successfully",
                apk=apk_info
            )
        except Exception as e:
            return ApkUploadResponse(
                success=False,
                message=f"Failed to upload APK: {str(e)}"
            )
    
    def delete_apk(self, apk_id: str) -> ApkActionResponse:
        """Delete an APK."""
        try:
            apks = self.list_apks()
            apk = next((a for a in apks if a.id == apk_id), None)
            
            if not apk:
                return ApkActionResponse(
                    success=False,
                    message="APK not found"
                )
            
            # Delete file
            if apk.file_path and os.path.exists(apk.file_path):
                os.remove(apk.file_path)

            # Delete metadata
            self.metadata.delete(apk_id)
            
            return ApkActionResponse(
                success=True,
                message="APK deleted successfully"
            )
        except Exception as e:
            return ApkActionResponse(
                success=False,
                message=f"Failed to delete APK: {str(e)}"
            )
    
    def install_apk(self, device_id: str, apk_id: str) -> ApkActionResponse:
        """Install APK to device."""
        try:
            apk = self.get_apk(apk_id)
            if not apk or not apk.file_path:
                return ApkActionResponse(
                    success=False,
                    message="APK not found"
                )
            
            # Use ADB to install
            cmd = f"adb -s {device_id} install -r {apk.file_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                return ApkActionResponse(
                    success=True,
                    message="APK installed successfully"
                )
            else:
                return ApkActionResponse(
                    success=False,
                    message=f"Failed to install APK: {result.stderr}"
                )
        except subprocess.TimeoutExpired:
            return ApkActionResponse(
                success=False,
                message="APK installation timed out"
            )
        except Exception as e:
            return ApkActionResponse(
                success=False,
                message=f"Failed to install APK: {str(e)}"
            )
