"""Tests for DeviceService — verifies the critical bugfix behavior."""

import pytest
from unittest.mock import patch, MagicMock
from app.services.device_service import DeviceService
from app.schemas.device import (
    DeviceInfo, DeviceStatus, PlatformType, ConnectionType
)


@pytest.fixture
def device_service():
    return DeviceService()


# --- disconnect_device: only disconnects TCP/IP devices, not USB ---


class TestDisconnectDevice:
    """Verify disconnect_device only runs adb disconnect for tcpip devices."""

    def test_disconnect_tcpip_device_calls_adb_disconnect(self, device_service):
        """TCP/IP device: should call adb disconnect."""
        # Mock _discover_adb_devices to return a tcpip device
        tcpip_device_info = {
            "device_id": "192.168.1.100:5555",
            "name": "Test TCP Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "tcpip",
            "ip": "192.168.1.100",
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }

        with patch.object(device_service, '_discover_adb_devices', return_value=[tcpip_device_info]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]), \
             patch.object(device_service, '_run_adb_command') as mock_run:
            mock_run.return_value = ""  # adb disconnect output

            device_service.disconnect_device("192.168.1.100:5555")

            # Should have called adb disconnect for the tcpip device
            mock_run.assert_called_with("disconnect 192.168.1.100:5555")

    def test_disconnect_usb_device_does_not_call_adb_disconnect(self, device_service):
        """USB device: should NOT call adb disconnect."""
        # Mock _discover_adb_devices to return a USB device
        usb_device_info = {
            "device_id": "abc12345",
            "name": "Test USB Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "usb",
            "ip": None,
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }

        with patch.object(device_service, '_discover_adb_devices', return_value=[usb_device_info]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]), \
             patch.object(device_service, '_run_adb_command') as mock_run:
            mock_run.return_value = ""

            device_service.disconnect_device("abc12345")

            # Should NOT have called adb disconnect for a USB device
            calls = [str(c) for c in mock_run.call_args_list]
            disconnect_calls = [c for c in calls if "disconnect" in c]
            assert len(disconnect_calls) == 0, f"USB device should not trigger adb disconnect, but got: {disconnect_calls}"

    def test_disconnect_unknown_device_does_not_call_adb_disconnect(self, device_service):
        """Device not in list: should NOT call adb disconnect."""
        with patch.object(device_service, '_discover_adb_devices', return_value=[]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]), \
             patch.object(device_service, '_run_adb_command') as mock_run:
            mock_run.return_value = ""

            device_service.disconnect_device("nonexistent_device")

            mock_run.assert_not_called()


# --- list_devices: correct available_actions by connection_type ---


class TestListDevicesAvailableActions:
    """Verify list_devices assigns correct available_actions based on connection type."""

    def test_usb_device_has_wireless_action_not_disconnect(self, device_service):
        """USB device should have 'wireless' in actions, not 'disconnect'."""
        usb_device_info = {
            "device_id": "abc123",
            "name": "USB Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "usb",
            "ip": None,
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }

        with patch.object(device_service, '_discover_adb_devices', return_value=[usb_device_info]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]):
            devices = device_service.list_devices()

        assert len(devices) == 1
        device = devices[0]
        assert device.connection_type == ConnectionType.USB
        assert "wireless" in device.available_actions
        assert "disconnect" not in device.available_actions

    def test_tcpip_device_has_disconnect_action_not_wireless(self, device_service):
        """TCP/IP device should have 'disconnect' in actions, not 'wireless'."""
        tcpip_device_info = {
            "device_id": "192.168.1.50:5555",
            "name": "TCP Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "tcpip",
            "ip": "192.168.1.50",
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }

        with patch.object(device_service, '_discover_adb_devices', return_value=[tcpip_device_info]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]):
            devices = device_service.list_devices()

        assert len(devices) == 1
        device = devices[0]
        assert device.connection_type == ConnectionType.TCPIP
        assert "disconnect" in device.available_actions
        assert "wireless" not in device.available_actions

    def test_both_usb_and_tcpip_devices_have_correct_actions(self, device_service):
        """When both USB and TCP/IP devices exist, each gets its own actions."""
        usb_info = {
            "device_id": "usb_dev",
            "name": "USB Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "usb",
            "ip": None,
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }
        tcpip_info = {
            "device_id": "192.168.1.1:5555",
            "name": "TCP Device",
            "platform": "android",
            "status": "connected",
            "connection_type": "tcpip",
            "ip": "192.168.1.1",
            "model": None,
            "manufacturer": None,
            "os_version": None,
            "screen_width": None,
            "screen_height": None,
            "battery_level": None,
            "device_type": None,
            "android_sdk_version": None,
        }

        with patch.object(device_service, '_discover_adb_devices', return_value=[usb_info, tcpip_info]), \
             patch.object(device_service, '_discover_hdc_devices', return_value=[]):
            devices = device_service.list_devices()

        assert len(devices) == 2

        usb_device = next(d for d in devices if d.connection_type == ConnectionType.USB)
        tcpip_device = next(d for d in devices if d.connection_type == ConnectionType.TCPIP)

        assert "wireless" in usb_device.available_actions
        assert "disconnect" not in usb_device.available_actions
        assert "disconnect" in tcpip_device.available_actions
        assert "wireless" not in tcpip_device.available_actions


# --- enable_tcpip_mode: uses -s device_id parameter ---


class TestEnableTcpipMode:
    """Verify enable_tcpip_mode uses adb -s {device_id} tcpip {port}."""

    def test_enable_tcpip_includes_device_serial(self, device_service):
        """The adb command should include -s {device_id} parameter."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "restarting in TCP mode port: 5555"

        with patch('app.services.device_service.subprocess.run', return_value=mock_result) as mock_run, \
             patch('app.services.device_service.time.sleep'):
            result = device_service.enable_tcpip_mode("abc12345", port=5555)

            # Verify subprocess.run was called with the correct command
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get('args', '')

            # The command string should contain -s abc12345
            assert "adb -s abc12345 tcpip 5555" in cmd, f"Expected 'adb -s abc12345 tcpip 5555' in command, got: {cmd}"

            assert result is True

    def test_enable_tcpip_mode_custom_port(self, device_service):
        """Custom port should be passed to adb command."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "restarting in TCP mode port: 6666"

        with patch('app.services.device_service.subprocess.run', return_value=mock_result) as mock_run, \
             patch('app.services.device_service.time.sleep'):
            result = device_service.enable_tcpip_mode("device789", port=6666)

            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get('args', '')

            assert "adb -s device789 tcpip 6666" in cmd
            assert result is True

    def test_enable_tcpip_mode_failure(self, device_service):
        """Failed tcpip mode should return False."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error: no device"

        with patch('app.services.device_service.subprocess.run', return_value=mock_result), \
             patch('app.services.device_service.time.sleep'):
            result = device_service.enable_tcpip_mode("missing_device")

            assert result is False


# --- enable_wireless_connection: orchestrates tcpip + connect ---


class TestEnableWirelessConnection:
    """Verify enable_wireless_connection calls get_device_ip then enable_tcpip_mode then connect_tcpip."""

    def test_enable_wireless_no_ip_returns_failure(self, device_service):
        """If device IP cannot be obtained, return failure without attempting tcpip."""
        with patch.object(device_service, 'get_device_ip', return_value=None):
            result = device_service.enable_wireless_connection("usb_device")

            assert result["success"] is False
            assert "IP" in result["message"] or "无法获取设备IP地址" in result["message"]

    def test_enable_wireless_tcpip_failure_returns_failure(self, device_service):
        """If tcpip mode fails, return failure."""
        with patch.object(device_service, 'get_device_ip', return_value="192.168.1.50"), \
             patch.object(device_service, 'enable_tcpip_mode', return_value=False):
            result = device_service.enable_wireless_connection("usb_device")

            assert result["success"] is False
            assert "TCP/IP" in result["message"] or "无法开启TCP/IP模式" in result["message"]

    def test_enable_wireless_success(self, device_service):
        """Full successful flow: get IP -> enable tcpip -> connect."""
        with patch.object(device_service, 'get_device_ip', return_value="192.168.1.50"), \
             patch.object(device_service, 'enable_tcpip_mode', return_value=True), \
             patch.object(device_service, 'connect_tcpip', return_value=True), \
             patch('time.sleep'):
            result = device_service.enable_wireless_connection("usb_device", port=5555)

            assert result["success"] is True
            assert result["ip"] == "192.168.1.50"
            assert result["port"] == 5555