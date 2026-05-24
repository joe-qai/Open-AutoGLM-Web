"""Settings schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional


class SettingsBase(BaseModel):
    """Base settings model."""
    language: Optional[str] = None
    theme: Optional[str] = None


class SettingsUpdate(SettingsBase):
    """Settings update model."""
    pass


class Settings(SettingsBase):
    """Settings response model."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
