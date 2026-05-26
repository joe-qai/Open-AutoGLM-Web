"""Socket.IO Server for real-time video streaming with full scrcpy protocol support."""

import asyncio
import logging
import traceback
from typing import Dict

from app.services.scrcpy_streamer import ScrcpyStreamer, VideoPacket

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Active streamers and their tasks
_streamers: Dict[str, ScrcpyStreamer] = {}
_socket_streamers: Dict[str, str] = {}  # sid -> device_id
_device_locks: Dict[str, asyncio.Lock] = {}
_stream_tasks: Dict[str, asyncio.Task] = {}  # sid -> streaming task


async def _stream_packets(sid: str, streamer: ScrcpyStreamer, sio):
    """Stream video packets to client with proper metadata."""
    logger.info(f"Starting packet stream for {sid}")
    
    try:
        while streamer.running:
            packet: VideoPacket = await streamer.read_packet()
            if not packet:
                break
            
            # Send video data to client with frame metadata
            await sio.emit("video-data", {
                "data": packet.data.hex(),
                "pts": packet.pts,
                "isKeyframe": packet.is_keyframe,
                "isConfig": packet.is_config,
            }, to=sid)
            
            # Throttle to prevent overwhelming client
            await asyncio.sleep(0.005)
            
    except asyncio.CancelledError:
        logger.info(f"Packet stream cancelled for {sid}")
    except Exception as e:
        logger.error(f"Error streaming to {sid}: {e}", exc_info=True)
        await sio.emit("error", {"message": f"视频流传输错误: {str(e)}", "type": "stream_error"}, to=sid)
    finally:
        logger.info(f"Stopped packet stream for {sid}")


async def connect_device(sio, sid: str, data: dict):
    """Handle device connection request with concurrency control."""
    device_id = data.get("device_id")
    max_size = int(data.get("maxSize") or 1280)
    bit_rate = int(data.get("bitRate") or 4_000_000)
    
    logger.info(f"Received connect-device for device {device_id} from {sid}")
    
    if not device_id:
        logger.error("device_id is required but not provided")
        await sio.emit("error", {
            "message": "请提供设备ID",
            "type": "missing_device_id"
        }, to=sid)
        return
    
    # Get device lock to prevent concurrent connections
    device_lock = _device_locks.setdefault(device_id, asyncio.Lock())
    
    async with device_lock:
        # Stop existing streamers for this device (except current client)
        sids_to_stop = [s for s, did in _socket_streamers.items() 
                        if s != sid and did == device_id]
        for s in sids_to_stop:
            await _stop_stream_for_sid(s, sio)
        
        # Create and start streamer
        try:
            logger.info(f"Creating ScrcpyStreamer for device {device_id} with max_size={max_size}, bit_rate={bit_rate}")
            streamer = ScrcpyStreamer(
                device_id=device_id,
                max_size=max_size,
                bit_rate=bit_rate,
            )
            
            logger.info(f"Starting streamer for device {device_id}")
            metadata = await streamer.start()
            
            _streamers[device_id] = streamer
            _socket_streamers[sid] = device_id
            
            # Send metadata
            logger.info(f"Sending video-metadata for device {device_id}: {metadata.device_name} ({metadata.width}x{metadata.height})")
            await sio.emit("video-metadata", {
                "deviceName": metadata.device_name,
                "width": metadata.width,
                "height": metadata.height,
                "codec": metadata.codec,
            }, to=sid)
            
            # Start streaming task
            logger.info(f"Starting packet streaming task for {sid}")
            task = asyncio.create_task(_stream_packets(sid, streamer, sio))
            _stream_tasks[sid] = task
            
            # Add callback for task completion
            def task_done_callback(fut):
                try:
                    fut.result()
                except Exception as e:
                    logger.error(f"Streaming task failed for {sid}: {e}")
                finally:
                    _stream_tasks.pop(sid, None)
            
            task.add_done_callback(task_done_callback)
            
        except Exception as e:
            err_type_name = type(e).__name__
            err_msg = str(e) or f"{err_type_name} (no detail message)"
            tb = traceback.format_exc()
            logger.error(f"Failed to start stream for {device_id}:\n{tb}")
            
            # Categorize error for user-friendly message
            error_type = "connection_failed"
            error_message = err_msg
            
            full_detail = f"[{err_type_name}] {err_msg}\n{tb}"
            
            if err_type_name == "NotImplementedError":
                error_type = "not_implemented"
                error_message = "该操作在Windows平台暂不支持，请确认ADB和设备连接后重试"
            if "device offline" in err_msg.lower() or "no devices/emulators found" in err_msg.lower():
                error_type = "device_offline"
                error_message = "设备无响应，请检查USB/WiFi连接"
            elif "port" in err_msg.lower() or "address already in use" in err_msg.lower():
                error_type = "port_conflict"
                error_message = "端口冲突，视频流端口仍被占用"
            elif "timeout" in err_msg.lower():
                error_type = "timeout"
                error_message = "连接超时，请检查设备连接后重试"
            elif err_type_name == "FileNotFoundError":
                error_message = f"ADB 未找到，请检查 ADB 安装"
            
            await sio.emit("error", {
                "message": error_message,
                "type": error_type,
                "technical_details": full_detail
            }, to=sid)


async def _stop_stream_for_sid(sid: str, sio):
    """Stop stream for a specific client."""
    device_id = _socket_streamers.get(sid)
    if device_id:
        # Cancel streaming task
        task = _stream_tasks.pop(sid, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Stop streamer
        streamer = _streamers.pop(device_id, None)
        if streamer:
            await streamer.stop()
        
        del _socket_streamers[sid]
        logger.info(f"Stream stopped for sid {sid}, device {device_id}")


async def disconnect_device(sio, sid: str):
    """Handle client disconnection."""
    logger.info(f"Client disconnecting: {sid}")
    await _stop_stream_for_sid(sid, sio)


async def initialize_socketio(app):
    """Initialize Socket.IO server with proper CORS and event handlers."""
    from socketio import AsyncServer
    
    # Configure CORS for Socket.IO - handles both Socket.IO and HTTP requests
    allowed_origins = ["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001", "null"]
    
    sio = AsyncServer(
        async_mode="asgi",
        cors_allowed_origins=allowed_origins,
        logger=True,
        engineio_logger=True,
        max_http_buffer_size=10 * 1024 * 1024  # 10MB for video frames
    )
    
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")
    
    @sio.event
    async def disconnect(sid):
        logger.info(f"Client disconnected: {sid}")
        await disconnect_device(sio, sid)
    
    @sio.event
    async def connect_device(sid, data):
        await connect_device(sio, sid, data)

    @sio.event
    async def disconnect_device(sid):
        await disconnect_device(sio, sid)
    
    # Mount Socket.IO to app
    from socketio import ASGIApp
    app.mount("/socket.io", ASGIApp(sio))
    
    return sio
