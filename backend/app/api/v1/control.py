"""Device control API endpoints."""

import asyncio
import subprocess
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TapRequest(BaseModel):
    """Request model for tap operation."""
    device_id: str
    x: int
    y: int


class TapResponse(BaseModel):
    """Response model for tap operation."""
    success: bool


class SwipeRequest(BaseModel):
    """Request model for swipe operation."""
    device_id: str
    start_x: int
    start_y: int
    end_x: int
    end_y: int
    duration_ms: int = 300


class SwipeResponse(BaseModel):
    """Response model for swipe operation."""
    success: bool


class TouchDownRequest(BaseModel):
    """Request model for touch down operation."""
    device_id: str
    x: int
    y: int


class TouchMoveRequest(BaseModel):
    """Request model for touch move operation."""
    device_id: str
    x: int
    y: int


class TouchUpRequest(BaseModel):
    """Request model for touch up operation."""
    device_id: str
    x: int
    y: int


class TouchResponse(BaseModel):
    """Response model for touch operations."""
    success: bool


def _find_adb():
    """Find ADB executable path."""
    paths = [
        "adb",
        os.path.join(os.environ.get("ANDROID_HOME", ""), "platform-tools", "adb"),
        os.path.join(os.environ.get("ANDROID_SDK_ROOT", ""), "platform-tools", "adb"),
    ]
    
    for path in paths:
        try:
            result = subprocess.run([path, "version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return path
        except:
            continue
    return "adb"


async def _run_adb_command(device_id: str, command: str):
    """Run ADB command asynchronously."""
    adb_path = _find_adb()
    cmd = [adb_path]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(command.split())
    
    try:
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=False,
            timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ADB command failed: {str(e)}")


@router.post("/{device_id}/tap", response_model=TapResponse)
async def control_tap(device_id: str, x: int, y: int) -> TapResponse:
    """Perform a tap operation on the device."""
    success = await _run_adb_command(device_id, f"shell input tap {x} {y}")
    return TapResponse(success=success)


@router.post("/{device_id}/swipe", response_model=SwipeResponse)
async def control_swipe(device_id: str, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> SwipeResponse:
    """Perform a swipe operation on the device."""
    success = await _run_adb_command(
        device_id,
        f"shell input swipe {start_x} {start_y} {end_x} {end_y} {duration_ms}"
    )
    return SwipeResponse(success=success)


class TouchRequest(BaseModel):
    """Request model for touch operation."""
    x: int
    y: int
    action: str = "down"


@router.post("/{device_id}/touch")
async def control_touch(device_id: str, request: TouchRequest) -> TouchResponse:
    """Send touch event to the device."""
    if request.action == "down":
        success = await _run_adb_command(device_id, f"shell input tap {request.x} {request.y}")
    else:
        success = True
    return TouchResponse(success=success)


@router.post("/{device_id}/touch/down", response_model=TouchResponse)
async def control_touch_down(device_id: str, x: int, y: int) -> TouchResponse:
    """Send touch down event to the device."""
    success = await _run_adb_command(device_id, f"shell input tap {x} {y}")
    return TouchResponse(success=success)


@router.post("/{device_id}/touch/move", response_model=TouchResponse)
async def control_touch_move(device_id: str, x: int, y: int) -> TouchResponse:
    """Send touch move event to the device."""
    success = True
    return TouchResponse(success=success)


@router.post("/{device_id}/touch/up", response_model=TouchResponse)
async def control_touch_up(device_id: str, x: int, y: int) -> TouchResponse:
    """Send touch up event to the device."""
    success = True
    return TouchResponse(success=success)


# AutoGLM-GUI compatible endpoints
class AutoGLMTouchRequest(BaseModel):
    """Request model for AutoGLM-GUI touch operation."""
    x: int
    y: int
    device_id: str
    delay: int = 0


@router.post("/touch/down")
async def control_touch_down_autoglm(request: AutoGLMTouchRequest) -> TouchResponse:
    """Send touch down event to the device (AutoGLM-GUI compatible)."""
    success = await _run_adb_command(request.device_id, f"shell input touchscreen down {request.x} {request.y}")
    return TouchResponse(success=success)


@router.post("/touch/up")
async def control_touch_up_autoglm(request: AutoGLMTouchRequest) -> TouchResponse:
    """Send touch up event to the device (AutoGLM-GUI compatible)."""
    success = await _run_adb_command(request.device_id, f"shell input touchscreen up {request.x} {request.y}")
    return TouchResponse(success=success)


@router.post("/touch/move")
async def control_touch_move_autoglm(request: AutoGLMTouchRequest) -> TouchResponse:
    """Send touch move event to the device (AutoGLM-GUI compatible)."""
    success = await _run_adb_command(request.device_id, f"shell input touchscreen move {request.x} {request.y}")
    return TouchResponse(success=success)


@router.post("/{device_id}/text")
async def control_text(device_id: str, text: str):
    """Input text on the device."""
    success = await _run_adb_command(device_id, f"shell input text {text}")
    return {"success": success}


@router.post("/{device_id}/keyevent")
async def control_keyevent(device_id: str, keycode: int):
    """Send key event to the device."""
    success = await _run_adb_command(device_id, f"shell input keyevent {keycode}")
    return {"success": success}


@router.post("/{device_id}/home")
async def control_home(device_id: str):
    """Press home button."""
    success = await _run_adb_command(device_id, "shell input keyevent 3")
    return {"success": success}


@router.post("/{device_id}/back")
async def control_back(device_id: str):
    """Press back button."""
    success = await _run_adb_command(device_id, "shell input keyevent 4")
    return {"success": success}


@router.post("/{device_id}/recent")
async def control_recent(device_id: str):
    """Press recent apps button."""
    success = await _run_adb_command(device_id, "shell input keyevent 187")
    return {"success": success}


@router.post("/{device_id}/volume_up")
async def control_volume_up(device_id: str):
    """Press volume up button."""
    success = await _run_adb_command(device_id, "shell input keyevent 24")
    return {"success": success}


@router.post("/{device_id}/volume_down")
async def control_volume_down(device_id: str):
    """Press volume down button."""
    success = await _run_adb_command(device_id, "shell input keyevent 25")
    return {"success": success}


@router.post("/{device_id}/power")
async def control_power(device_id: str):
    """Press power button."""
    success = await _run_adb_command(device_id, "shell input keyevent 26")
    return {"success": success}
