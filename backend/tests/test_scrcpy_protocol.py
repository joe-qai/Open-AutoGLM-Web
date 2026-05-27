"""Tests for Scrcpy protocol constants and data structures."""

import pytest
from app.services.scrcpy_protocol import (
    SCRCPY_CODEC_H264,
    SCRCPY_CODEC_H265,
    SCRCPY_CODEC_AV1,
    SCRCPY_CODEC_NAME_TO_ID,
    SCRCPY_KNOWN_CODECS,
    PTS_CONFIG,
    PTS_KEYFRAME,
    ScrcpyVideoStreamMetadata,
    ScrcpyMediaStreamPacket,
    ScrcpyVideoStreamOptions,
    ScrcpyServerOptions,
)


class TestCodecConstants:
    """Verify codec constants match Scrcpy protocol."""

    def test_h264_codec_value(self):
        """H264 codec constant should be correct."""
        # "h264" in ASCII hex
        assert SCRCPY_CODEC_H264 == 0x68323634
        assert hex(SCRCPY_CODEC_H264) == "0x68323634"

    def test_h265_codec_value(self):
        """H265 codec constant should be correct."""
        # "h265" in ASCII hex
        assert SCRCPY_CODEC_H265 == 0x68323635
        assert hex(SCRCPY_CODEC_H265) == "0x68323635"

    def test_av1_codec_value(self):
        """AV1 codec constant should be correct."""
        # "av1" in ASCII hex (padded)
        assert SCRCPY_CODEC_AV1 == 0x00617631
        assert hex(SCRCPY_CODEC_AV1) == "0x617631" or hex(SCRCPY_CODEC_AV1) == "0x00617631"

    def test_codec_name_to_id_mapping(self):
        """Codec name to ID mapping should be correct."""
        assert SCRCPY_CODEC_NAME_TO_ID["h264"] == SCRCPY_CODEC_H264
        assert SCRCPY_CODEC_NAME_TO_ID["h265"] == SCRCPY_CODEC_H265
        assert SCRCPY_CODEC_NAME_TO_ID["av1"] == SCRCPY_CODEC_AV1

    def test_known_codecs_set(self):
        """Known codecs set should contain all codecs."""
        assert SCRCPY_CODEC_H264 in SCRCPY_KNOWN_CODECS
        assert SCRCPY_CODEC_H265 in SCRCPY_KNOWN_CODECS
        assert SCRCPY_CODEC_AV1 in SCRCPY_KNOWN_CODECS


class TestPtsConstants:
    """Verify PTS (Presentation Time Stamp) constants."""

    def test_pts_config_value(self):
        """PTS_CONFIG should be 1 << 63."""
        assert PTS_CONFIG == 1 << 63
        assert PTS_CONFIG == 0x8000000000000000

    def test_pts_keyframe_value(self):
        """PTS_KEYFRAME should be 1 << 62."""
        assert PTS_KEYFRAME == 1 << 62
        assert PTS_KEYFRAME == 0x4000000000000000

    def test_pts_flags_do_not_overlap(self):
        """PTS flags should not overlap."""
        assert (PTS_CONFIG & PTS_KEYFRAME) == 0


class TestVideoStreamMetadata:
    """Verify video stream metadata data class."""

    def test_metadata_creation(self):
        """Metadata should be created with correct fields."""
        metadata = ScrcpyVideoStreamMetadata(
            device_name="Test Device",
            width=1080,
            height=1920,
            codec=SCRCPY_CODEC_H264,
        )
        
        assert metadata.device_name == "Test Device"
        assert metadata.width == 1080
        assert metadata.height == 1920
        assert metadata.codec == SCRCPY_CODEC_H264

    def test_metadata_optional_fields(self):
        """Optional fields should default to None."""
        metadata = ScrcpyVideoStreamMetadata(
            device_name=None,
            width=None,
            height=None,
            codec=SCRCPY_CODEC_H264,
        )
        
        assert metadata.device_name is None
        assert metadata.width is None
        assert metadata.height is None
        assert metadata.codec == SCRCPY_CODEC_H264


class TestMediaStreamPacket:
    """Verify media stream packet data class."""

    def test_packet_creation(self):
        """Packet should be created with correct fields."""
        packet = ScrcpyMediaStreamPacket(
            type="data",
            data=b"\x00\x01\x02",
            keyframe=True,
            pts=12345,
        )
        
        assert packet.type == "data"
        assert packet.data == b"\x00\x01\x02"
        assert packet.keyframe is True
        assert packet.pts == 12345

    def test_packet_default_values(self):
        """Optional fields should default to None."""
        packet = ScrcpyMediaStreamPacket(
            type="configuration",
            data=b"config",
        )
        
        assert packet.keyframe is None
        assert packet.pts is None


class TestVideoStreamOptions:
    """Verify video stream options defaults."""

    def test_default_options(self):
        """Default options should have correct values."""
        options = ScrcpyVideoStreamOptions()
        
        assert options.send_device_meta is True
        assert options.send_codec_meta is True
        assert options.send_frame_meta is True
        assert options.send_dummy_byte is True
        assert options.video_codec == "h264"

    def test_custom_options(self):
        """Custom options should override defaults."""
        options = ScrcpyVideoStreamOptions(
            send_device_meta=False,
            video_codec="h265",
        )
        
        assert options.send_device_meta is False
        assert options.video_codec == "h265"
        # Other fields should remain default
        assert options.send_frame_meta is True


class TestServerOptions:
    """Verify server options data class."""

    def test_server_options_creation(self):
        """Server options should be created with all required fields."""
        options = ScrcpyServerOptions(
            max_size=1080,
            bit_rate=8000000,
            max_fps=20,
            tunnel_forward=True,
            audio=False,
            control=False,
            cleanup=False,
            video_codec="h264",
            send_frame_meta=True,
            send_device_meta=True,
            send_codec_meta=True,
            send_dummy_byte=True,
            video_codec_options="i-frame-interval=1",
        )
        
        assert options.max_size == 1080
        assert options.bit_rate == 8000000
        assert options.max_fps == 20
        assert options.tunnel_forward is True
        assert options.audio is False
        assert options.control is False