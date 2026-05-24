"""Project service for managing projects — SQLite persistence."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.db import db
from app.schemas.project import Project, ProjectCreate, ProjectUpdate


class ProjectService:

    async def create_project(self, project_create: ProjectCreate) -> Project:
        project_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn = await db.get_connection()
        await conn.execute(
            """INSERT INTO projects (project_id, name, description, platform, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (project_id, project_create.name, project_create.description,
             "cross", now, now)
        )
        await conn.commit()
        return Project(project_id=project_id, name=project_create.name,
                       description=project_create.description,
                       created_at=datetime.fromisoformat(now),
                       updated_at=datetime.fromisoformat(now))

    async def get_project(self, project_id: str) -> Optional[Project]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return Project(project_id=row["project_id"], name=row["name"],
                       description=row["description"],
                       created_at=datetime.fromisoformat(row["created_at"]),
                       updated_at=datetime.fromisoformat(row["updated_at"]))

    async def list_projects(self) -> List[Project]:
        conn = await db.get_connection()
        cursor = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [Project(project_id=r["project_id"], name=r["name"],
                        description=r["description"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                        updated_at=datetime.fromisoformat(r["updated_at"]))
                for r in rows]

    async def update_project(self, project_id: str, project_update: ProjectUpdate) -> Optional[Project]:
        existing = await self.get_project(project_id)
        if not existing:
            return None
        conn = await db.get_connection()
        fields = []
        values = []
        if project_update.name is not None:
            fields.append("name = ?")
            values.append(project_update.name)
        if project_update.description is not None:
            fields.append("description = ?")
            values.append(project_update.description)
        if fields:
            fields.append("updated_at = ?")
            values.append(datetime.now(timezone.utc).isoformat())
            values.append(project_id)
            await conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE project_id = ?", values)
            await conn.commit()
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> bool:
        conn = await db.get_connection()
        cursor = await conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
        await conn.commit()
        return cursor.rowcount > 0
