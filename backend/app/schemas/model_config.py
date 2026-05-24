"""Model configuration schemas."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from enum import Enum

class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class ModelConfigBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    provider: ModelProvider
    base_url: Optional[str] = None
    api_key: str
    model_name: str
    is_default: bool = False

class ModelConfigCreate(ModelConfigBase):
    pass

class ModelConfigTestResponse(BaseModel):
    success: bool
    message: str
    response_time_ms: Optional[float] = None

class ModelConfigUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: Optional[str] = None
    provider: Optional[ModelProvider] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None

class ModelConfigResponse(ModelConfigBase):
    config_id: str
    created_at: str
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
