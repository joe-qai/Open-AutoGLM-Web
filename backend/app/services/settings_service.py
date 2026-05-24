"""Settings service for managing application settings."""

from typing import Dict, Optional

from app.schemas.settings import Settings, SettingsUpdate


class SettingsService:
    """Service for settings management."""

    def __init__(self):
        self.settings: Dict[str, Optional[str]] = {
            "language": "cn",
            "theme": "light"
        }

    def get_settings(self) -> Settings:
        """Get current settings."""
        return Settings(**self.settings)

    def update_settings(self, settings_update: SettingsUpdate) -> Settings:
        """Update settings."""
        update_data = settings_update.model_dump(exclude_unset=True)
        self.settings.update(update_data)
        return Settings(**self.settings)

    def reset_settings(self) -> Settings:
        """Reset settings to default."""
        self.settings = {
            "language": "cn",
            "theme": "light"
        }
        return Settings(**self.settings)
