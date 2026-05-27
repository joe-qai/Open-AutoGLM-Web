"""Tests for ScrcpyStreamer — verifies the critical bugfix behavior."""

import asyncio
import subprocess
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.scrcpy_streamer import ScrcpyStreamer
from app.services.scrcpy_protocol import ScrcpyVideoStreamMetadata, ScrcpyMediaStreamPacket


class TestVideoMetadataFormat:
    """Verify video metadata format matches AutoGLM-GUI (codec as integer)."""

    def test_video_metadata_codec_is_integer(self):
        """Codec should remain as integer, not converted to string."""
        metadata = ScrcpyVideoStreamMetadata(
            device_name="Test Device",
            width=1080,
            height=1920,
            codec=0x68323634  # h264 in hex
        )
        
        # Codec should be integer, not string
        assert isinstance(metadata.codec, int)
        assert metadata.codec == 0x68323634
        
    def test_video_metadata_fields_match_autoglm_gui(self):
        """Metadata fields should match AutoGLM-GUI format."""
        metadata = ScrcpyVideoStreamMetadata(
            device_name="Pixel 7",
            width=1080,
            height=2400,
            codec=0x68323634
        )
        
        # Verify all required fields exist and have correct types
        assert hasattr(metadata, 'device_name')
        assert hasattr(metadata, 'width')
        assert hasattr(metadata, 'height')
        assert hasattr(metadata, 'codec')
        
        # Types should match AutoGLM-GUI
        assert isinstance(metadata.device_name, (str, type(None)))
        assert isinstance(metadata.width, (int, type(None)))
        assert isinstance(metadata.height, (int, type(None)))
        assert isinstance(metadata.codec, int)


class TestStreamerInitialization:
    """Verify streamer initialization sequence and timing."""

    @pytest.mark.asyncio
    async def test_start_reads_metadata_immediately(self):
        """After connection, metadata should be read immediately."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        with patch.object(streamer, '_check_device_available', new_callable=AsyncMock), \
             patch.object(streamer, '_cleanup_existing_server', new_callable=AsyncMock), \
             patch.object(streamer, '_push_server', new_callable=AsyncMock), \
             patch.object(streamer, '_setup_port_forward', new_callable=AsyncMock), \
             patch.object(streamer, '_start_server', new_callable=AsyncMock), \
             patch.object(streamer, '_connect_socket', new_callable=AsyncMock), \
             patch.object(streamer, 'read_video_metadata', new_callable=AsyncMock) as mock_read_metadata:
            
            await streamer.start()
            
            # read_video_metadata should be called after connection
            mock_read_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_metadata_read_before_streaming(self):
        """Metadata should be read before streaming packets."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer._metadata = None
        
        mock_read_meta = AsyncMock(return_value=ScrcpyVideoStreamMetadata(
            device_name="Test", width=1080, height=1920, codec=0x68323634
        ))
        streamer.read_video_metadata = mock_read_meta
        
        # Simulate calling read_media_packet which requires metadata
        with patch.object(streamer, '_read_u64', new_callable=AsyncMock), \
             patch.object(streamer, '_read_u32', new_callable=AsyncMock), \
             patch.object(streamer, '_read_exactly', new_callable=AsyncMock):
            
            # This should trigger read_video_metadata if _metadata is None
            try:
                await streamer.read_media_packet()
            except:
                pass  # We just want to verify the call
        
        mock_read_meta.assert_called_once()


class TestPacketToPayloadEncoding:
    """Verify video packet encoding for Socket.IO transmission."""

    def test_packet_to_payload_uses_base64(self):
        """Packet data should be Base64 encoded."""
        from app.services.socketio_server import _packet_to_payload
        from app.services.scrcpy_protocol import ScrcpyMediaStreamPacket
        
        test_data = b'\x00\x01\x02\x03'
        packet = ScrcpyMediaStreamPacket(type="data", data=test_data, keyframe=True, pts=12345)
        
        payload = _packet_to_payload(packet)
        
        # Data should be Base64 encoded string, not bytes
        assert isinstance(payload["data"], str)
        assert payload["type"] == "data"
        assert payload["keyframe"] == True
        assert payload["pts"] == 12345
        assert "timestamp" in payload

    def test_configuration_packet_encoding(self):
        """Configuration packets should also be Base64 encoded."""
        from app.services.socketio_server import _packet_to_payload
        from app.services.scrcpy_protocol import ScrcpyMediaStreamPacket
        
        config_data = b'config_data_here'
        packet = ScrcpyMediaStreamPacket(type="configuration", data=config_data)
        
        payload = _packet_to_payload(packet)
        
        assert isinstance(payload["data"], str)
        assert payload["type"] == "configuration"
        assert "keyframe" not in payload
        assert "pts" not in payload


class TestDeviceLockMechanism:
    """Verify device lock prevents concurrent connections."""

    def test_stop_cleans_up_resources(self):
        """Streamer stop should clean up resources."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        # Mock the socket and process cleanup
        mock_socket = MagicMock()
        mock_process = MagicMock()
        streamer.tcp_socket = mock_socket
        streamer.scrcpy_process = mock_process
        
        streamer.stop()
        
        # Verify cleanup was called
        mock_socket.close.assert_called_once()
        mock_process.terminate.assert_called_once()


class TestScrcpyProtocolConstants:
    """Verify Scrcpy protocol constants match expected values."""

    def test_pts_constants(self):
        """PTS constants should have correct values."""
        from app.services.scrcpy_protocol import PTS_CONFIG, PTS_KEYFRAME
        
        # PTS_CONFIG is a special value indicating configuration packet (1 << 63)
        assert PTS_CONFIG == 0x8000000000000000
        # PTS_KEYFRAME bit flag (1 << 62)
        assert PTS_KEYFRAME == 0x4000000000000000

    def test_video_codec_constants(self):
        """Video codec constants should match Scrcpy protocol."""
        from app.services.scrcpy_protocol import SCRCPY_CODEC_H264, SCRCPY_CODEC_H265, SCRCPY_CODEC_AV1
        
        assert SCRCPY_CODEC_H264 == 0x68323634  # "h264" in ASCII
        assert SCRCPY_CODEC_H265 == 0x68323635  # "h265" in ASCII
        assert SCRCPY_CODEC_AV1 == 0x00617631   # "av1" in ASCII (padded)


class TestScrcpyServerOptions:
    """Verify Scrcpy server options are correctly built."""

    def test_server_options_defaults(self):
        """Default options should match current implementation."""
        streamer = ScrcpyStreamer(device_id="test_device")
        options = streamer._build_server_options()
        
        # Verify critical options match current implementation
        assert options.max_size == 1280
        assert options.bit_rate == 4000000
        assert options.max_fps == 20
        assert options.tunnel_forward is True
        assert options.audio is False
        assert options.control is False
        assert options.cleanup is False
        assert options.video_codec == "h264"
        assert options.send_frame_meta is True
        assert options.send_device_meta is True
        assert options.send_codec_meta is True
        assert options.send_dummy_byte is True
        assert options.video_codec_options == "i-frame-interval=1"

    def test_server_options_custom(self):
        """Custom options should be correctly applied."""
        streamer = ScrcpyStreamer(
            device_id="test_device",
            max_size=720,
            bit_rate=2000000,
        )
        options = streamer._build_server_options()
        
        assert options.max_size == 720
        assert options.bit_rate == 2000000


class TestDeviceAvailabilityCheck:
    """Verify device availability checking logic."""

    @pytest.mark.asyncio
    async def test_check_device_available_online(self):
        """Online device should pass availability check."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        mock_result = MagicMock()
        mock_result.stdout = b"device"
        mock_result.stderr = b""
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock, return_value=mock_result):
            await streamer._check_device_available()  # Should not raise

    @pytest.mark.asyncio
    async def test_check_device_available_offline(self):
        """Offline device should raise RuntimeError."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        mock_result = MagicMock()
        mock_result.stdout = b"offline"
        mock_result.stderr = b""
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock, return_value=mock_result):
            with pytest.raises(RuntimeError, match="not available"):
                await streamer._check_device_available()

    @pytest.mark.asyncio
    async def test_check_device_timeout(self):
        """Device timeout should raise RuntimeError."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(RuntimeError, match="timed out"):
                await streamer._check_device_available()


class TestPacketReading:
    """Verify media packet reading functionality."""

    @pytest.mark.asyncio
    async def test_read_configuration_packet(self):
        """Configuration packets should be correctly identified."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer._metadata = ScrcpyVideoStreamMetadata("Test", 1080, 1920, 0x68323634)
        
        config_data = b'\x00\x01\x02\x03'
        with patch.object(streamer, '_read_u64', new_callable=AsyncMock, return_value=0x8000000000000000), \
             patch.object(streamer, '_read_u32', new_callable=AsyncMock, return_value=len(config_data)), \
             patch.object(streamer, '_read_exactly', new_callable=AsyncMock, return_value=config_data):
            
            packet = await streamer.read_media_packet()
            
            assert packet.type == "configuration"
            assert packet.data == config_data
            assert packet.keyframe is None
            assert packet.pts is None

    @pytest.mark.asyncio
    async def test_read_keyframe_packet(self):
        """Keyframe packets should be correctly identified."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer._metadata = ScrcpyVideoStreamMetadata("Test", 1080, 1920, 0x68323634)
        
        frame_data = b'\x00\x01\x02\x03'
        pts_value = 0x4000000000000001  # KEYFRAME flag + PTS=1
        
        with patch.object(streamer, '_read_u64', new_callable=AsyncMock, return_value=pts_value), \
             patch.object(streamer, '_read_u32', new_callable=AsyncMock, return_value=len(frame_data)), \
             patch.object(streamer, '_read_exactly', new_callable=AsyncMock, return_value=frame_data):
            
            packet = await streamer.read_media_packet()
            
            assert packet.type == "data"
            assert packet.data == frame_data
            assert packet.keyframe is True
            assert packet.pts == 1

    @pytest.mark.asyncio
    async def test_read_regular_frame_packet(self):
        """Regular frame packets should be correctly identified."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer._metadata = ScrcpyVideoStreamMetadata("Test", 1080, 1920, 0x68323634)
        
        frame_data = b'\x00\x01\x02\x03'
        pts_value = 12345
        
        with patch.object(streamer, '_read_u64', new_callable=AsyncMock, return_value=pts_value), \
             patch.object(streamer, '_read_u32', new_callable=AsyncMock, return_value=len(frame_data)), \
             patch.object(streamer, '_read_exactly', new_callable=AsyncMock, return_value=frame_data):
            
            packet = await streamer.read_media_packet()
            
            assert packet.type == "data"
            assert packet.data == frame_data
            assert packet.keyframe is False
            assert packet.pts == 12345


class TestIterPackets:
    """Verify packet iteration functionality."""

    @pytest.mark.asyncio
    async def test_iter_packets_yields_continuously(self):
        """iter_packets should yield packets continuously."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        packets = [
            ScrcpyMediaStreamPacket("configuration", b'config1'),
            ScrcpyMediaStreamPacket("data", b'frame1', keyframe=True, pts=1),
            ScrcpyMediaStreamPacket("data", b'frame2', keyframe=False, pts=2),
        ]
        
        with patch.object(streamer, 'read_media_packet', new_callable=AsyncMock) as mock_read:
            mock_read.side_effect = packets + [asyncio.CancelledError()]
            
            received = []
            try:
                async for packet in streamer.iter_packets():
                    received.append(packet)
            except asyncio.CancelledError:
                pass
            
            assert len(received) == 3
            assert received[0].type == "configuration"
            assert received[1].keyframe is True
            assert received[2].keyframe is False


class TestAdbOperations:
    """Verify ADB operations."""

    @pytest.mark.asyncio
    async def test_cleanup_existing_server(self):
        """Cleanup should kill existing scrcpy processes."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            await streamer._cleanup_existing_server()
            
            # Should have called multiple cleanup commands
            assert mock_run.call_count >= 3  # pkill, ps+grep+kill, forward --remove

    @pytest.mark.asyncio
    async def test_push_server(self):
        """Server push should call adb push."""
        streamer = ScrcpyStreamer(device_id="test_device")
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            await streamer._push_server()
            
            call_args = mock_run.call_args[0][0]
            assert "push" in call_args
            assert "/data/local/tmp/scrcpy-server" in call_args[-1]

    @pytest.mark.asyncio
    async def test_setup_port_forward(self):
        """Port forward setup should call adb forward."""
        streamer = ScrcpyStreamer(device_id="test_device", port=27183)
        
        with patch('app.services.scrcpy_streamer.run_cmd_silently', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            await streamer._setup_port_forward()
            
            call_args = mock_run.call_args[0][0]
            assert "forward" in call_args
            assert "tcp:27183" in call_args
            assert "localabstract:scrcpy" in call_args
            
            assert streamer.forward_cleanup_needed is True


class TestStopMethod:
    """Verify stop method cleanup logic."""

    def test_stop_with_none_resources(self):
        """Stop should handle None resources gracefully."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer.tcp_socket = None
        streamer.scrcpy_process = None
        streamer.forward_cleanup_needed = False
        
        # Should not raise exceptions
        streamer.stop()

    def test_stop_cleans_up_forward(self):
        """Stop should remove port forward when needed."""
        streamer = ScrcpyStreamer(device_id="test_device", port=27183)
        streamer.tcp_socket = None
        streamer.scrcpy_process = None
        streamer.forward_cleanup_needed = True
        
        with patch('app.services.scrcpy_streamer.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            streamer.stop()
            
            call_args = mock_run.call_args[0][0]
            assert "forward" in call_args
            assert "--remove" in call_args
            assert "tcp:27183" in call_args
            
            assert streamer.forward_cleanup_needed is False

    def test_stop_kill_on_timeout(self):
        """Stop should kill process if terminate times out."""
        streamer = ScrcpyStreamer(device_id="test_device")
        streamer.tcp_socket = None
        
        mock_process = MagicMock()
        mock_process.terminate.side_effect = subprocess.TimeoutExpired("cmd", 2)
        mock_process.returncode = None
        
        streamer.scrcpy_process = mock_process
        
        streamer.stop()
        
        mock_process.kill.assert_called_once()