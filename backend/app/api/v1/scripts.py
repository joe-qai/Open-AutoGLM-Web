"""Script management API."""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
from app.schemas.script import ScriptResponse, ScriptCreate, ScriptUpdate, ScriptType
from app.services.script_service import ScriptService
from app.services.task_service import TaskService

router = APIRouter()
script_service = ScriptService()


@router.post("/", response_model=ScriptResponse)
async def create_script(script: ScriptCreate):
    script_id = await script_service.create_script(
        name=script.name,
        content=script.content,
        script_type=script.script_type,
        platform=script.platform,
        project_id=script.project_id,
        description=script.description,
    )
    return await script_service.get_script(script_id)


@router.get("/{script_id}", response_model=ScriptResponse)
async def get_script(script_id: str):
    script = await script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/{script_id}", response_model=ScriptResponse)
async def update_script(script_id: str, update: ScriptUpdate):
    result = await script_service.update_script(script_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Script not found")
    return result


@router.delete("/{script_id}")
async def delete_script(script_id: str):
    await script_service.delete_script(script_id)
    return {"message": "Script deleted successfully"}


@router.get("/")
async def list_scripts(
    project_id: Optional[str] = None,
    script_type: Optional[ScriptType] = None,
    platform: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    scripts = await script_service.list_scripts(project_id, script_type, platform, skip, limit)
    return {"scripts": scripts}


@router.post("/{script_id}/execute")
async def execute_script(script_id: str, data: dict, background_tasks: BackgroundTasks):
    script = await script_service.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    device_id = data.get("device_id")
    model_config_id = data.get("model_config_id")
    task_id = await script_service.execute_script(script_id, device_id, model_config_id)
    if not task_id:
        raise HTTPException(status_code=400, detail="Failed to create task for script execution")
    task_service = TaskService()
    background_tasks.add_task(task_service.execute_task, task_id)
    return {"task_id": task_id, "script_id": script_id, "status": "executing"}


@router.post("/generate")
async def generate_script(
    task_description: str,
    platform: str,
    project_id: Optional[str] = None,
):
    script_id = await script_service.generate_script(task_description, platform, project_id)
    return await script_service.get_script(script_id)


@router.post("/{script_id}/derive")
async def derive_script(script_id: str, platform: str):
    new_script_id = await script_service.derive_script(script_id, platform)
    return await script_service.get_script(new_script_id)


@router.get("/{script_id}/versions")
async def get_script_versions(script_id: str):
    versions = await script_service.get_script_versions(script_id)
    return {"versions": versions}


@router.post("/{script_id}/save-version")
async def save_script_version(script_id: str, content: str, comment: str = ""):
    version_id = await script_service.save_script_version(script_id, content, comment)
    return {"version_id": version_id}


@router.post("/upload")
async def upload_script(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    platform: str = Form("android"),
):
    if not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Only Python files (.py) are allowed")
    content = await file.read()
    content_str = content.decode("utf-8")
    script_id = await script_service.create_script(
        name=name,
        content=content_str,
        script_type="external",
        platform=platform,
        project_id=None,
        description=description,
    )
    return await script_service.get_script(script_id)
