"""Model configuration service for managing different LLM providers."""

import time
from typing import List, Optional
from app.db import db
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse

class ModelConfigService:
    async def create_config(self, config: ModelConfigCreate) -> str:
        config_id = f"mcfg_{int(time.time_ns())}"
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        conn = await db.get_connection()
        
        # If this is set as default, unset others
        if config.is_default:
            await conn.execute("UPDATE model_configs SET is_default = 0")
            
        await conn.execute(
            """INSERT INTO model_configs (config_id, name, provider, base_url, api_key, model_name, is_default, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (config_id, config.name, config.provider.value, config.base_url, config.api_key, 
             config.model_name, 1 if config.is_default else 0, now, now)
        )
        await conn.commit()
        return config_id

    async def get_config(self, config_id: str) -> Optional[ModelConfigResponse]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM model_configs WHERE config_id = ?", (config_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return ModelConfigResponse(**dict(row))

    async def list_configs(self) -> List[ModelConfigResponse]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM model_configs ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [ModelConfigResponse(**dict(row)) for row in rows]

    async def update_config(self, config_id: str, update: ModelConfigUpdate) -> Optional[ModelConfigResponse]:
        conn = await db.get_connection()
        
        # Check if exists
        existing = await self.get_config(config_id)
        if not existing:
            return None
            
        fields = []
        values = []
        update_data = update.model_dump(exclude_unset=True)
        
        if 'is_default' in update_data and update_data['is_default']:
            await conn.execute("UPDATE model_configs SET is_default = 0")
            
        for k, v in update_data.items():
            fields.append(f"{k} = ?")
            values.append(v)
            
        if fields:
            fields.append("updated_at = ?")
            values.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
            values.append(config_id)
            await conn.execute(f"UPDATE model_configs SET {', '.join(fields)} WHERE config_id = ?", values)
            await conn.commit()
            
        return await self.get_config(config_id)

    async def delete_config(self, config_id: str):
        conn = await db.get_connection()
        await conn.execute("DELETE FROM model_configs WHERE config_id = ?", (config_id,))
        await conn.commit()

    async def get_default_config(self) -> Optional[ModelConfigResponse]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM model_configs WHERE is_default = 1")
        row = await cursor.fetchone()
        if not row:
            # Fallback to the latest created if no default is set
            cursor = await conn.execute("SELECT * FROM model_configs ORDER BY created_at DESC LIMIT 1")
            row = await cursor.fetchone()
            
        if not row:
            return None
        return ModelConfigResponse(**dict(row))
