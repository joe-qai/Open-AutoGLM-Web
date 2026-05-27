"""Socket.IO server for Scrcpy video streaming."""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

from typing_extensions import TypedDict, NotRequired

import socketio

from app.logger import logger
from app.services.scrcpy_protocol import ScrcpyMediaStreamPacket
from app.services.scrcpy_streamer import ScrcpyStreamer


class VideoPacketPayload(TypedDict):
    type: str
    data: str  # Hex encoded
    timestamp: int
    isConfig: bool
    isKeyframe: NotRequired[bool | None]
    pts: NotRequired[int | None]


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    transports=["websocket", "polling"],
    allow_upgrades=True,
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10 * 1024 * 1024,
    server_kwargs={"socketio_path": "/socket.io"},
)


async def initialize_socketio(app: Any) -> None:
    """Initialize Socket.IO server and attach to FastAPI app."""
    from socketio import ASGIApp

    socketio_app = ASGIApp(sio)
    app.mount("/socket.io", socketio_app)

_socket_streamers: dict[str, ScrcpyStreamer] = {}
_stream_tasks: dict[str, asyncio.Task[None]] = {}
_device_locks: dict[
    str, asyncio.Lock
] = {}  # Lock per device to prevent concurrent connections


async def _stop_stream_for_sid(sid: str) -> None:
    task = _stream_tasks.pop(sid, None)
    if task:
        task.cancel()

    streamer = _socket_streamers.pop(sid, None)
    if streamer:
        streamer.stop()


def _classify_error(exc: Exception) -> dict[str, Any]:
    """Classify error and return user-friendly message."""
    error_str = str(exc)

    if "Address already in use" in error_str or (
        "Port" in error_str and "occupied" in error_str
    ):
        return {
            "message": "端口冲突，视频流端口仍被占用。通常会自动解决，如果持续出现请重启应用。",
            "type": "port_conflict",
            "technical_details": error_str,
        }
    elif "Device" in error_str and (
        "not available" in error_str or "not found" in error_str
    ):
        return {
            "message": "设备无响应，请检查 USB/WiFi 连接。",
            "type": "device_offline",
            "technical_details": error_str,
        }
    elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
        return {
            "message": "连接超时，请检查设备连接后重试。",
            "type": "timeout",
            "technical_details": error_str,
        }
    elif "Failed to connect" in error_str:
        return {
            "message": "无法连接到 scrcpy 服务器，请检查设备连接。",
            "type": "connection_failed",
            "technical_details": error_str,
        }
    else:
        return {
            "message": error_str,
            "type": "unknown",
            "technical_details": error_str,
        }


def stop_streamers(device_id: str | None = None) -> None:
    """Stop active scrcpy streamers (all or by device)."""
    sids = list(_socket_streamers.keys())
    for sid in sids:
        streamer = _socket_streamers.get(sid)
        if not streamer:
            continue
        if device_id and streamer.device_id != device_id:
            continue
        task = _stream_tasks.pop(sid, None)
        if task:
            task.cancel()
        streamer.stop()
        _socket_streamers.pop(sid, None)


async def _stream_packets(sid: str, streamer: ScrcpyStreamer) -> None:
    try:
        logger.info(f"Starting video packet streaming for sid: {sid}")
        packet_count = 0
        async for packet in streamer.iter_packets():
            payload = _packet_to_payload(packet)
            await sio.emit("video-data", payload, to=sid)
            packet_count += 1
            if packet_count % 30 == 0:
                logger.debug(f"Sent {packet_count} video packets to sid: {sid}")
            if packet.type == "configuration":
                logger.debug(f"Sent configuration packet (size: {len(packet.data)})")
            elif packet.type == "data" and packet.keyframe:
                logger.debug(f"Sent keyframe packet (size: {len(packet.data)})")
    except asyncio.CancelledError:
        logger.info(f"Video streaming cancelled for sid: {sid}")
        raise
    except Exception as exc:
        logger.exception("Video streaming failed: %s", exc)
        try:
            await sio.emit("error", {"message": str(exc)}, to=sid)
        except Exception as emit_exc:
            logger.debug(
                "Failed to emit Socket.IO stream error to %s: %s", sid, emit_exc
            )
    finally:
        logger.info(f"Stopping video streaming for sid: {sid}")
        await _stop_stream_for_sid(sid)


def _bytes_to_hex(data: bytes) -> str:
    """Convert bytes to hex string for WebSocket transmission."""
    return data.hex()

def _packet_to_payload(packet: ScrcpyMediaStreamPacket) -> VideoPacketPayload:
    payload: VideoPacketPayload = {
        "type": packet.type,
        "data": _bytes_to_hex(packet.data),
        "timestamp": int(time.time() * 1000),
        "isConfig": packet.type == "configuration",
        "isKeyframe": packet.keyframe if packet.type == "data" else None,
        "pts": packet.pts if packet.type == "data" else None,
    }
    return payload


@sio.event
async def connect(sid: str, environ: dict[str, Any]) -> None:
    logger.info("Socket.IO client connected: %s", sid)


@sio.event
async def disconnect(sid: str) -> None:
    logger.info("Socket.IO client disconnected: %s", sid)
    await _stop_stream_for_sid(sid)


@sio.on("connect-device")
async def connect_device(sid: str, data: dict[str, Any] | None) -> None:
    payload = data or {}
    device_id = payload.get("device_id") or payload.get("deviceId")
    if not device_id:
        await sio.emit(
            "error",
            {"message": "Device ID is required", "type": "invalid_request"},
            to=sid,
        )
        return

    max_size = int(payload.get("maxSize") or payload.get("max_size") or 1280)
    bit_rate = int(payload.get("bitRate") or payload.get("bit_rate") or 4_000_000)

    await _stop_stream_for_sid(sid)

    if device_id not in _device_locks:
        _device_locks[device_id] = asyncio.Lock()

    device_lock = _device_locks[device_id]

    async with device_lock:
        logger.debug(f"Acquired device lock for {device_id}, sid: {sid}")

        sids_to_stop = [
            s
            for s, streamer in _socket_streamers.items()
            if s != sid and streamer.device_id == device_id
        ]
        for s in sids_to_stop:
            logger.info(f"Stopping existing stream for device {device_id} from sid {s}")
            await _stop_stream_for_sid(s)

        streamer = ScrcpyStreamer(
            device_id=device_id,
            max_size=max_size,
            bit_rate=bit_rate,
        )

        try:
            await streamer.start()
            metadata = await streamer.read_video_metadata()
            
            await sio.emit(
                "video-metadata",
                {
                    "deviceName": metadata.device_name,
                    "width": metadata.width,
                    "height": metadata.height,
                    "codec": metadata.codec,
                },
                to=sid,
            )

            _socket_streamers[sid] = streamer
            _stream_tasks[sid] = asyncio.create_task(_stream_packets(sid, streamer))

        except Exception as exc:
            streamer.stop()
            logger.exception("Failed to start scrcpy stream: %s", exc)
            error_info = _classify_error(exc)
            await sio.emit("error", error_info, to=sid)