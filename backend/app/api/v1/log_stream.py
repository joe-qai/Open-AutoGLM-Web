"""Log streaming API using Server-Sent Events (SSE)."""

import asyncio
from typing import Optional, Set
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
import json
import time

from app.logger import logger as app_logger

router = APIRouter()

# Store active SSE clients
_active_clients: Set[asyncio.Queue] = set()


async def log_stream_generator(
    level: Optional[str] = None,
    category: Optional[str] = None,
    task_id: Optional[str] = None,
    device_id: Optional[str] = None,
):
    """Generate log stream for SSE."""
    queue = asyncio.Queue(maxsize=100)
    _active_clients.add(queue)
    
    try:
        # Send initial message
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Log stream connected'})}\n\n"
        
        while True:
            try:
                # Wait for new log with timeout
                log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # Apply filters
                if level and log_entry.get('level') != level.upper():
                    continue
                if category and log_entry.get('category') != category:
                    continue
                if task_id and log_entry.get('task_id') != task_id:
                    continue
                if device_id and log_entry.get('device_id') != device_id:
                    continue
                
                yield f"data: {json.dumps(log_entry)}\n\n"
            except asyncio.TimeoutError:
                # Send keep-alive message
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        _active_clients.discard(queue)


@router.get("/stream")
async def stream_logs(
    level: Optional[str] = Query(None, description="Filter by log level: DEBUG, INFO, WARNING, ERROR"),
    category: Optional[str] = Query(None, description="Filter by category: api, script, task, device, system"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    device_id: Optional[str] = Query(None, description="Filter by device ID"),
):
    """Stream logs in real-time using Server-Sent Events (SSE).
    
    Clients can subscribe to receive log updates as they happen.
    Supports filtering by level, category, task_id, and device_id.
    """
    return StreamingResponse(
        log_stream_generator(level=level, category=category, task_id=task_id, device_id=device_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


def broadcast_log(
    level: str,
    category: str,
    message: str,
    task_id: Optional[str] = None,
    device_id: Optional[str] = None,
    **kwargs
):
    """Broadcast a log message to all connected SSE clients.
    
    This function should be called whenever a new log entry is created.
    """
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "level": level.upper(),
        "category": category,
        "message": message,
        "task_id": task_id,
        "device_id": device_id,
        **kwargs,
    }
    
    # Send to all active clients
    for queue in list(_active_clients):
        try:
            queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            # Client is slow, skip this message
            pass
    
    # Also log to standard logger
    log_method = getattr(app_logger, level.lower(), app_logger.info)
    log_method(f"[{category}] {message}")
