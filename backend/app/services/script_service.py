"""Script service for managing test scripts — SQLite persistence."""

from typing import List, Optional
import time
from datetime import datetime

from app.db import db
from app.schemas.script import ScriptResponse, ScriptType, ScriptUpdate


class ScriptService:

    async def create_script(
        self,
        name: str,
        content: str,
        script_type: str,
        platform: str,
        project_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        script_id = f"script_{int(time.time_ns())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO scripts (script_id, name, content, script_type, platform, project_id, description, created_at, updated_at, version)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (script_id, name, content, script_type, platform, project_id, description, timestamp, timestamp)
        )
        await conn.commit()
        return script_id

    async def get_script(self, script_id: str) -> Optional[ScriptResponse]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM scripts WHERE script_id = ?", (script_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return ScriptResponse(
            script_id=row["script_id"],
            name=row["name"],
            content=row["content"],
            script_type=ScriptType(row["script_type"]),
            platform=row["platform"],
            project_id=row["project_id"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            version=row["version"]
        )

    async def update_script(self, script_id: str, update: ScriptUpdate) -> Optional[ScriptResponse]:
        existing = await self.get_script(script_id)
        if not existing:
            return None
        conn = await db.get_connection()
        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.content is not None:
            fields.append("content = ?")
            values.append(update.content)
            fields.append("version = version + 1")
        if update.description is not None:
            fields.append("description = ?")
            values.append(update.description)
        if fields:
            fields.append("updated_at = ?")
            values.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
            values.append(script_id)
            await conn.execute(f"UPDATE scripts SET {', '.join(fields)} WHERE script_id = ?", values)
            await conn.commit()
        return await self.get_script(script_id)

    async def delete_script(self, script_id: str) -> None:
        conn = await db.get_connection()
        await conn.execute("DELETE FROM scripts WHERE script_id = ?", (script_id,))
        await conn.commit()

    async def list_scripts(
        self,
        project_id: Optional[str] = None,
        script_type: Optional[ScriptType] = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScriptResponse]:
        conn = await db.get_connection()
        conditions = []
        params = []
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if script_type:
            conditions.append("script_type = ?")
            params.append(script_type.value)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        cursor = await conn.execute(f"SELECT * FROM scripts {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [limit, skip])
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            result.append(ScriptResponse(
                script_id=row["script_id"],
                name=row["name"],
                content=row["content"],
                script_type=ScriptType(row["script_type"]),
                platform=row["platform"],
                project_id=row["project_id"],
                description=row["description"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                version=row["version"]
            ))
        return result

    async def execute_script(self, script_id: str, device_id: Optional[str] = None, model_config_id: Optional[str] = None) -> str:
        from app.services.task_service import TaskService
        script = await self.get_script(script_id)
        if not script:
            return ""
        task_service = TaskService()
        task_id = await task_service.create_task(
            name=f"Execute: {script.name}",
            description=f"Script execution: {script.name}",
            script_id=script_id,
            device_id=device_id,
            platform=script.platform,
            model_config_id=model_config_id,
        )
        return task_id

    async def generate_script(self, task_description: str, platform: str, project_id: Optional[str] = None) -> str:
        script_content = self._generate_script_content(task_description, platform)
        return await self.create_script(
            name=f"Generated Script - {task_description[:30]}",
            content=script_content,
            script_type="ai_generated",
            platform=platform,
            project_id=project_id,
            description=f"Auto-generated script for: {task_description}"
        )

    def _generate_script_content(self, task_description: str, platform: str) -> str:
        timestamp = datetime.now().isoformat()
        if platform == "android":
            return f'''# Android Script (Python + uiautomator2)
# Generated: {timestamp}
# Task: {task_description}

import uiautomator2 as u2
import time

d = u2.connect()

try:
    print("Script execution started")
finally:
    pass
'''
        elif platform == "ios":
            return f'''// iOS Script (XCTest)
// Generated: {timestamp}
// Task: {task_description}

import XCTest

class GeneratedTest: XCTestCase {{
    var app: XCUIApplication!

    override func setUp() {{
        super.setUp()
        app = XCUIApplication()
        app.launch()
    }}

    func testTask() {{
    }}
}}
'''
        elif platform == "harmonyos":
            return f'''// HarmonyOS Script (Hypium)
// Generated: {timestamp}
// Task: {task_description}

import ohos.hypium.Hypium;
import ohos.hypium.executor.Action;
import ohos.hypium.executor.Executor;

public class GeneratedTest {{
    public static void main(String[] args) {{
        Executor executor = Hypium.createExecutor();
        try {{
        }} finally {{
            executor.release();
        }}
    }}
}}
'''
        else:
            return f'''# Generic Script\n# Generated: {timestamp}\n# Task: {task_description}\n'''

    async def derive_script(self, script_id: str, platform: str) -> str:
        original_script = await self.get_script(script_id)
        if not original_script:
            return ""
        new_content = self._generate_script_content(
            original_script.description or original_script.name, platform
        )
        return await self.create_script(
            name=f"{original_script.name} ({platform})",
            content=new_content,
            script_type="ai_generated",
            platform=platform,
            project_id=original_script.project_id,
            description=f"Derived from {script_id}"
        )

    async def save_script_version(self, script_id: str, content: str, comment: str = "") -> str:
        conn = await db.get_connection()
        await conn.execute(
            "UPDATE scripts SET content = ?, version = version + 1, updated_at = ? WHERE script_id = ?",
            (content, time.strftime("%Y-%m-%dT%H:%M:%S"), script_id)
        )
        await conn.commit()
        script = await self.get_script(script_id)
        return f"v{script.version}" if script else "v1"

    async def get_script_versions(self, script_id: str) -> List[dict]:
        script = await self.get_script(script_id)
        if not script:
            return []
        return [{
            "version_id": f"v{script.version}",
            "script_id": script_id,
            "content": script.content,
            "version_number": script.version,
            "created_at": script.updated_at or script.created_at,
            "comment": ""
        }]
