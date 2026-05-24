"""Project schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ProjectBase(BaseModel):
    """Base project model."""
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Project creation model."""
    pass


class ProjectUpdate(BaseModel):
    """Project update model."""
    name: Optional[str] = None
    description: Optional[str] = None


class Project(ProjectBase):
    """Project response model."""
    project_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
