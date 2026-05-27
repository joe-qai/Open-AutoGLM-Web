"""Tests for SettingsService."""

import pytest
from app.services.settings_service import SettingsService
from app.schemas.settings import SettingsUpdate


class TestSettingsService:
    """Verify settings service functionality."""

    def test_get_settings(self):
        """Should return current settings."""
        service = SettingsService()
        settings = service.get_settings()
        
        assert settings is not None
        assert settings.language == "cn"
        assert settings.theme == "light"

    def test_update_settings(self):
        """Should update settings successfully."""
        service = SettingsService()
        
        update = SettingsUpdate(language="en", theme="dark")
        updated_settings = service.update_settings(update)
        
        assert updated_settings.language == "en"
        assert updated_settings.theme == "dark"

    def test_update_settings_partial(self):
        """Should update only specified settings."""
        service = SettingsService()
        
        # Reset to defaults first
        service.reset_settings()
        
        update = SettingsUpdate(theme="dark")
        updated_settings = service.update_settings(update)
        
        # Only theme should change, language remains default
        assert updated_settings.language == "cn"
        assert updated_settings.theme == "dark"

    def test_reset_settings(self):
        """Should reset settings to defaults."""
        service = SettingsService()
        
        # First change some settings
        update = SettingsUpdate(language="en", theme="dark")
        service.update_settings(update)
        
        # Verify changes
        assert service.get_settings().language == "en"
        assert service.get_settings().theme == "dark"
        
        # Reset to defaults
        reset_settings = service.reset_settings()
        
        # Verify defaults restored
        assert reset_settings.language == "cn"
        assert reset_settings.theme == "light"

    def test_settings_persistence(self):
        """Should maintain settings state within instance."""
        service = SettingsService()
        
        # Change settings
        update = SettingsUpdate(language="en")
        service.update_settings(update)
        
        # Get settings again - should reflect changes
        settings = service.get_settings()
        assert settings.language == "en"