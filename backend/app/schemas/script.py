"""Script schemas."""

from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import Optional, List


class ScriptType(str, Enum):
    """Script type classification."""
    AI_GENERATED = "ai_generated"
    IMPORTED = "imported"
    MANUAL = "manual"
    EXTERNAL = "external"


class ScriptCreate(BaseModel):
    """Request model for creating a script."""
    name: str
    content: str
    script_type: ScriptType
    platform: str
    project_id: Optional[str] = None
    description: Optional[str] = None


class ScriptUpdate(BaseModel):
    """Request model for updating a script."""
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None


class ScriptResponse(BaseModel):
    """Response model for script information."""
    script_id: str
    name: str
    content: str
    script_type: ScriptType
    platform: str
    project_id: Optional[str] = None
    description: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ScriptVersion(BaseModel):
    """Script version information."""
    version_id: str
    script_id: str
    content: str
    version_number: int
    created_at: str
    comment: Optional[str] = None
