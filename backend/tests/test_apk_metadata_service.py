"""Tests for ApkMetadataService."""

import pytest
from app.services.apk_metadata_service import ApkMetadataService


class TestApkMetadataService:
    """Verify APK metadata service functionality."""

    def test_save_metadata(self):
        """Should save APK metadata successfully."""
        service = ApkMetadataService()
        
        apk_id = service.save(
            apk_id="apk123",
            original_filename="test.apk",
            package_name="com.example.app",
            version="1.0.0",
            file_size=1024,
            upload_time="2024-01-01T00:00:00",
            status="uploaded",
        )
        
        assert apk_id == "apk123"

    def test_get_metadata(self):
        """Should retrieve APK metadata by apk_id."""
        service = ApkMetadataService()
        
        # First save metadata
        service.save(
            apk_id="apk456",
            original_filename="test2.apk",
            package_name="com.example.app2",
            version="2.0.0",
            upload_time="2024-01-01T00:00:00",
        )
        
        # Then retrieve it
        metadata = service.get("apk456")
        
        assert metadata is not None
        assert metadata["apk_id"] == "apk456"
        assert metadata["original_filename"] == "test2.apk"
        assert metadata["package_name"] == "com.example.app2"

    def test_get_metadata_not_found(self):
        """Should return None when metadata doesn't exist."""
        service = ApkMetadataService()
        metadata = service.get("nonexistent_apk")
        
        assert metadata is None

    def test_list_all_metadata(self):
        """Should list all APK metadata entries."""
        service = ApkMetadataService()
        
        # Add some entries
        service.save(apk_id="apk_list_1", original_filename="app1.apk", upload_time="2024-01-01T00:00:00")
        service.save(apk_id="apk_list_2", original_filename="app2.apk", upload_time="2024-01-02T00:00:00")
        
        entries = service.list_all()
        
        assert isinstance(entries, list)
        assert len(entries) >= 2

    def test_delete_metadata(self):
        """Should delete APK metadata."""
        service = ApkMetadataService()
        
        # First save metadata
        service.save(apk_id="apk_delete", original_filename="delete.me.apk", upload_time="2024-01-01T00:00:00")
        
        # Verify it exists
        assert service.get("apk_delete") is not None
        
        # Delete it
        result = service.delete("apk_delete")
        
        assert result is True
        
        # Verify it's gone
        assert service.get("apk_delete") is None

    def test_update_status(self):
        """Should update the status of an APK."""
        service = ApkMetadataService()
        
        # First save metadata
        service.save(apk_id="apk_status", original_filename="status.apk", status="uploaded", upload_time="2024-01-01T00:00:00")
        
        # Update status
        result = service.update_status("apk_status", "installed")
        
        assert result is True
        
        # Verify status changed
        metadata = service.get("apk_status")
        assert metadata["status"] == "installed"

    def test_singleton_pattern(self):
        """Should return the same instance each time."""
        service1 = ApkMetadataService()
        service2 = ApkMetadataService()
        
        assert service1 is service2