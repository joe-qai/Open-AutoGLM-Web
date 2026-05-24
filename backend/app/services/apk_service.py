"""APK management service — SQLite persistence + batch delete."""

import os
import uuid
import subprocess
import re
from typing import List, Optional
from datetime import datetime

from app.db import db
from app.schemas.apk import ApkInfo, ApkStatus, ApkUploadResponse, ApkActionResponse
from app.config import settings


class ApkService:

    def __init__(self):
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "apks")
        os.makedirs(self.upload_dir, exist_ok=True)

    def _parse_apk_info(self, file_path: str) -> dict:
        info = {"version": None, "package_name": None}
        for cmd_name in ["aapt2", "aapt"]:
            try:
                result = subprocess.run(
                    [cmd_name, "dump", "badging", file_path],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
                )
                if result.returncode == 0:
                    pkg_match = re.search(r"package: name='([^']+)'", result.stdout)
                    if pkg_match:
                        info["package_name"] = pkg_match.group(1)
                    ver_match = re.search(r"versionName='([^']+)'", result.stdout)
                    if ver_match:
                        info["version"] = ver_match.group(1)
                    return info
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return info

    async def list_apks(self) -> List[ApkInfo]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM apks ORDER BY upload_time DESC")
        rows = await cursor.fetchall()
        return [ApkInfo(
            id=r["id"], name=r["name"],
            original_filename=r["original_filename"],
            version=r["version"], package_name=r["package_name"],
            file_size=r["file_size"], file_path=r["file_path"],
            upload_time=datetime.fromisoformat(r["upload_time"]),
            status=ApkStatus(r["status"])
        ) for r in rows]

    async def get_apk(self, apk_id: str) -> Optional[ApkInfo]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM apks WHERE id = ?", (apk_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return ApkInfo(
            id=row["id"], name=row["name"],
            original_filename=row["original_filename"],
            version=row["version"], package_name=row["package_name"],
            file_size=row["file_size"], file_path=row["file_path"],
            upload_time=datetime.fromisoformat(row["upload_time"]),
            status=ApkStatus(row["status"])
        )

    async def upload_apk(self, file, filename: str) -> ApkUploadResponse:
        try:
            apk_id = str(uuid.uuid4())[:8]
            original_ext = os.path.splitext(filename)[1] or ".apk"
            saved_filename = f"{apk_id}{original_ext}"
            file_path = os.path.join(self.upload_dir, saved_filename)

            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            apk_info_data = self._parse_apk_info(file_path)

            conn = await db.get_connection()
            await conn.execute(
                """INSERT INTO apks (id, name, original_filename, package_name, version, file_size, file_path, upload_time, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (apk_id, filename, filename, apk_info_data.get("package_name"),
                 apk_info_data.get("version"), len(content), file_path,
                 datetime.now().isoformat(), "uploaded")
            )
            await conn.commit()

            apk_info = ApkInfo(
                id=apk_id, name=filename, original_filename=filename,
                version=apk_info_data.get("version"),
                package_name=apk_info_data.get("package_name"),
                file_size=len(content), upload_time=datetime.now(),
                status=ApkStatus.UPLOADED, file_path=file_path
            )
            return ApkUploadResponse(success=True, message="APK uploaded successfully", apk=apk_info)
        except Exception as e:
            return ApkUploadResponse(success=False, message=f"Failed to upload APK: {str(e)}")

    async def delete_apk(self, apk_id: str) -> ApkActionResponse:
        try:
            apk = await self.get_apk(apk_id)
            if not apk:
                return ApkActionResponse(success=False, message="APK not found")
            if apk.file_path and os.path.exists(apk.file_path):
                os.remove(apk.file_path)
            conn = await db.get_connection()
            await conn.execute("DELETE FROM apks WHERE id = ?", (apk_id,))
            await conn.commit()
            return ApkActionResponse(success=True, message="APK deleted successfully")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to delete APK: {str(e)}")

    async def delete_apk_batch(self, apk_ids: List[str]) -> ApkActionResponse:
        try:
            conn = await db.get_connection()
            for apk_id in apk_ids:
                apk = await self.get_apk(apk_id)
                if apk and apk.file_path and os.path.exists(apk.file_path):
                    os.remove(apk.file_path)
                await conn.execute("DELETE FROM apks WHERE id = ?", (apk_id,))
            await conn.commit()
            return ApkActionResponse(success=True, message=f"{len(apk_ids)} APK(s) deleted successfully")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to batch delete APKs: {str(e)}")

    async def install_apk(self, device_id: str, apk_id: str) -> ApkActionResponse:
        try:
            apk = await self.get_apk(apk_id)
            if not apk or not apk.file_path:
                return ApkActionResponse(success=False, message="APK not found")
            result = subprocess.run(
                ["adb", "-s", device_id, "install", "-r", apk.file_path],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300
            )
            if result.returncode == 0:
                return ApkActionResponse(success=True, message="APK installed successfully")
            else:
                return ApkActionResponse(success=False, message=f"Failed to install APK: {result.stderr}")
        except subprocess.TimeoutExpired:
            return ApkActionResponse(success=False, message="APK installation timed out")
        except Exception as e:
            return ApkActionResponse(success=False, message=f"Failed to install APK: {str(e)}")
