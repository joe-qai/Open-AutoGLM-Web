"""Model configuration API."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.schemas.model_config import ModelConfigResponse, ModelConfigCreate, ModelConfigUpdate
from app.services.model_config_service import ModelConfigService

router = APIRouter()
model_config_service = ModelConfigService()

@router.post("/", response_model=ModelConfigResponse)
async def create_config(config: ModelConfigCreate):
    config_id = await model_config_service.create_config(config)
    return await model_config_service.get_config(config_id)

@router.get("/", response_model=List[ModelConfigResponse])
async def list_configs():
    return await model_config_service.list_configs()

@router.get("/{config_id}", response_model=ModelConfigResponse)
async def get_config(config_id: str):
    config = await model_config_service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Model configuration not found")
    return config

@router.put("/{config_id}", response_model=ModelConfigResponse)
async def update_config(config_id: str, update: ModelConfigUpdate):
    result = await model_config_service.update_config(config_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Model configuration not found")
    return result

@router.delete("/{config_id}")
async def delete_config(config_id: str):
    await model_config_service.delete_config(config_id)
    return {"message": "Model configuration deleted successfully"}

@router.get("/default", response_model=Optional[ModelConfigResponse])
async def get_default_config():
    return await model_config_service.get_default_config()
