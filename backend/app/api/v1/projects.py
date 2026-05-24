"""Project management API."""

from fastapi import APIRouter, HTTPException
from app.schemas.project import Project, ProjectCreate, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter()
project_service = ProjectService()


@router.get("/")
async def list_projects():
    """List all projects."""
    projects = await project_service.list_projects()
    return {"projects": projects}


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Get project details by ID."""
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=Project)
async def create_project(project_create: ProjectCreate):
    """Create a new project."""
    project = await project_service.create_project(project_create)
    return project


@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: str, project_update: ProjectUpdate):
    """Update an existing project."""
    project = await project_service.update_project(project_id, project_update)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project."""
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}
