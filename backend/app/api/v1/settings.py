"""Settings management API."""

from fastapi import APIRouter
from app.schemas.settings import Settings, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter()
settings_service = SettingsService()


@router.get("/", response_model=Settings)
async def get_settings():
    """Get current application settings."""
    settings = settings_service.get_settings()
    return settings


@router.put("/", response_model=Settings)
async def update_settings(settings_update: SettingsUpdate):
    """Update application settings."""
    settings = settings_service.update_settings(settings_update)
    return settings


@router.post("/reset", response_model=Settings)
async def reset_settings():
    """Reset settings to default values."""
    settings = settings_service.reset_settings()
    return settings
