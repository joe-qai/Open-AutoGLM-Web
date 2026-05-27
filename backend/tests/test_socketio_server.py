"""Tests for Socket.IO server — verifies video streaming functionality."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.socketio_server import (
    VideoPacketPayload,
    sio,
    _socket_streamers,
    _stream_tasks,
    _device_locks,
    _stop_stream_for_sid,
    _classify_error,
)
from app.services.scrcpy_streamer import ScrcpyStreamer
from app.services.scrcpy_protocol import ScrcpyMediaStreamPacket


class TestVideoPacketPayload:
    """Verify video packet payload structure."""

    def test_payload_has_required_fields(self):
        """Payload should have required fields."""
        payload: VideoPacketPayload = {
            "type": "data",
            "data": "base64_encoded_data",
            "timestamp": 1234567890,
        }
        
        assert "type" in payload
        assert "data" in payload
        assert "timestamp" in payload
        assert isinstance(payload["type"], str)
        assert isinstance(payload["data"], str)
        assert isinstance(payload["timestamp"], int)

    def test_payload_optional_fields(self):
        """Payload should support optional keyframe and pts fields."""
        payload: VideoPacketPayload = {
            "type": "data",
            "data": "base64_data",
            "timestamp": 1234567890,
            "keyframe": True,
            "pts": 100,
        }
        
        assert payload["keyframe"] is True
        assert payload["pts"] == 100


class TestDeviceLockMechanism:
    """Verify device lock prevents concurrent connections."""

    @pytest.mark.asyncio
    async def test_device_lock_is_unique_per_device(self):
        """Each device should have its own lock."""
        lock1 = _device_locks.setdefault("device1", asyncio.Lock())
        lock2 = _device_locks.setdefault("device1", asyncio.Lock())
        lock3 = _device_locks.setdefault("device2", asyncio.Lock())
        
        assert lock1 is lock2  # Same device, same lock
        assert lock1 is not lock3  # Different devices, different locks

    @pytest.mark.asyncio
    async def test_device_lock_acquired_concurrently(self):
        """Device lock should prevent concurrent access."""
        device_id = "test_device"
        counter = 0
        
        async def increment_with_lock():
            nonlocal counter
            lock = _device_locks.setdefault(device_id, asyncio.Lock())
            async with lock:
                # Simulate work
                await asyncio.sleep(0.01)
                counter += 1
        
        # Run multiple tasks concurrently
        tasks = [increment_with_lock() for _ in range(5)]
        await asyncio.gather(*tasks)
        
        # Counter should be 5 (no race condition)
        assert counter == 5


class TestStreamManagement:
    """Verify stream start/stop management."""

    @pytest.mark.asyncio
    async def test_stop_stream_cleans_up_resources(self):
        """Stopping stream should clean up streamer and task."""
        sid = "test_sid"
        
        # Setup
        mock_streamer = MagicMock(spec=ScrcpyStreamer)
        mock_task = MagicMock(spec=asyncio.Task)
        mock_task.cancel = MagicMock()
        
        _socket_streamers[sid] = mock_streamer
        _stream_tasks[sid] = mock_task
        
        await _stop_stream_for_sid(sid)
        
        # Verify cleanup
        mock_task.cancel.assert_called_once()
        mock_streamer.stop.assert_called_once()
        assert sid not in _socket_streamers
        assert sid not in _stream_tasks

    @pytest.mark.asyncio
    async def test_stop_stream_handles_missing_sid(self):
        """Stopping a non-existent stream should not raise errors."""
        # Should not raise any exceptions
        await _stop_stream_for_sid("nonexistent_sid")


class TestErrorClassification:
    """Verify error classification for user-friendly messages."""

    def test_classify_device_not_found_error(self):
        """Device not found errors should be classified correctly."""
        exc = RuntimeError("Device 11f16a99 not found")
        error_info = _classify_error(exc)
        
        assert error_info["type"] == "device_offline"
        assert "设备" in error_info["message"]

    def test_classify_port_conflict_error(self):
        """Port conflict errors should be classified correctly."""
        exc = RuntimeError("Address already in use")
        error_info = _classify_error(exc)
        
        assert error_info["type"] == "port_conflict"
        assert "端口" in error_info["message"]

    def test_classify_generic_error(self):
        """Unknown errors should fall back to generic classification."""
        exc = RuntimeError("Unknown error occurred")
        error_info = _classify_error(exc)
        
        assert error_info["type"] == "unknown"
        assert "Unknown error occurred" in error_info["message"]

    def test_classify_timeout_error(self):
        """Timeout errors should be classified correctly."""
        exc = RuntimeError("Connection timed out")
        error_info = _classify_error(exc)
        
        assert error_info["type"] == "timeout"
        assert "超时" in error_info["message"]


class TestPacketToPayload:
    """Verify packet conversion to payload."""

    def test_packet_to_payload_conversion(self):
        """Packets should be correctly converted to payload format."""
        from app.services.socketio_server import _packet_to_payload
        
        packet = ScrcpyMediaStreamPacket(
            type="data",
            data=b"\x00\x01\x02\x03",
            keyframe=True,
            pts=12345,
        )
        
        payload = _packet_to_payload(packet)
        
        assert payload["type"] == "data"
        assert isinstance(payload["data"], str)  # Hex encoded
        assert "timestamp" in payload
        assert payload["isConfig"] is False
        assert payload["isKeyframe"] is True
        assert payload["pts"] == 12345

    def test_configuration_packet_conversion(self):
        """Configuration packets should have isConfig=True."""
        from app.services.socketio_server import _packet_to_payload
        
        packet = ScrcpyMediaStreamPacket(
            type="configuration",
            data=b"config_data",
        )
        
        payload = _packet_to_payload(packet)
        
        assert payload["type"] == "configuration"
        assert payload["isConfig"] is True
        assert payload["isKeyframe"] is None
        assert payload["pts"] is None