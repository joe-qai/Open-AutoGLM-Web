"""Script management API."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import List, Optional
from app.schemas.script import ScriptResponse, ScriptCreate, ScriptUpdate, ScriptType
from app.services.script_service import ScriptService

router = APIRouter()
script_service = ScriptService()


@router.post("/", response_model=ScriptResponse)
async def create_script(script: ScriptCreate):
    """Create a new script."""
    script_id = script_service.create_script(
        name=script.name,
        content=script.content,
        script_type=script.script_type,
        platform=script.platform,
        project_id=script.project_id,
        description=script.description,
    )
    return script_service.get_script(script_id)


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: str):
    """Get script details."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: str, update: ScriptUpdate):
    """Update a script."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_service.update_script(script_id, update)
    return script_service.get_script(script_id)


@router.delete("/{script_id}")
async def delete_script(script_id: str):
    """Delete a script."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    script_service.delete_script(script_id)
    return {"message": "Script deleted successfully"}


@router.get("/")
async def list_scripts(
    project_id: str | None = None,
    script_type: ScriptType | None = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """List all scripts."""
    scripts = script_service.list_scripts(project_id, script_type, platform, skip, limit)
    return {"scripts": scripts}


@router.post("/{script_id}/execute")
async def execute_script(script_id: str, data: dict, background_tasks: BackgroundTasks):
    """Execute a script by creating a task. Returns the task_id."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    device_id = data.get("device_id")
    task_id = script_service.execute_script(script_id, device_id)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to create task for script execution")

    return {"task_id": task_id, "script_id": script_id, "status": "task_created"}


@router.post("/generate")
async def generate_script(
    task_description: str,
    platform: str,
    project_id: Optional[str] = None,
):
    """Generate a script from task description."""
    script_id = script_service.generate_script(task_description, platform, project_id)
    return script_service.get_script(script_id)


@router.post("/{script_id}/derive")
async def derive_script(script_id: str, platform: str):
    """Derive a script for a different platform."""
    script = script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    new_script_id = script_service.derive_script(script_id, platform)
    return script_service.get_script(new_script_id)


@router.get("/{script_id}/versions")
async def get_script_versions(script_id: str):
    """Get version history of a script."""
    versions = script_service.get_script_versions(script_id)
    return {"versions": versions}


@router.post("/{script_id}/save-version")
async def save_script_version(script_id: str, content: str, comment: str = ""):
    """Save a new version of the script."""
    version_id = script_service.save_script_version(script_id, content, comment)
    return {"version_id": version_id}


@router.post("/upload")
async def upload_script(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    platform: str = Form("android"),
):
    """Upload a script from local file."""
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python files (.py) are allowed")
    
    content = await file.read()
    content_str = content.decode("utf-8")
    
    script_id = script_service.create_script(
        name=name,
        content=content_str,
        script_type="external",
        platform=platform,
        project_id=None,
        description=description,
    )
    
    return script_service.get_script(script_id)
