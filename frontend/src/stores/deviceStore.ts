import { create } from 'zustand';
import { deviceApi } from '../services/api';

export interface Device {
  device_id: string;
  name: string;
  platform: 'android' | 'ios' | 'harmonyos';
  status: 'connected' | 'disconnected' | 'busy' | 'error';
  connection_type?: 'usb' | 'tcpip';
  ip?: string;
  model?: string;
  manufacturer?: string;
  os_version?: string;
  screen_width?: number;
  screen_height?: number;
  battery_level?: number;
}

interface DeviceState {
  devices: Device[];
  selectedDevice: Device | null;
  loading: boolean;
  connectingTcpIp: boolean;
  enablingWirelessDeviceId: string | null;
  error: string | null;
  success: string | null;
  screenshotData: string | null;
  loadingScreenshot: boolean;
  drawerOpen: boolean;

  // Actions
  fetchDevices: () => Promise<void>;
  selectDevice: (device: Device | null) => void;
  connectDevice: (deviceId: string) => Promise<void>;
  disconnectDevice: (deviceId: string) => Promise<void>;
  connectTcpIp: (ipPort: string) => Promise<void>;
  enableWireless: (deviceId: string, port?: number) => Promise<void>;
  getDeviceIp: (deviceId: string) => Promise<string | null>;
  clearMessages: () => void;
  openDrawer: (device: Device) => Promise<void>;
  closeDrawer: () => void;
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  devices: [],
  selectedDevice: null,
  loading: false,
  connectingTcpIp: false,
  enablingWirelessDeviceId: null,
  error: null,
  success: null,
  screenshotData: null,
  loadingScreenshot: false,
  drawerOpen: false,

  fetchDevices: async () => {
    set({ loading: true, error: null });
    try {
      const response = await deviceApi.getDevices() as unknown as { devices: Device[] };
      set({ devices: response.devices, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch devices', loading: false });
    }
  },

  selectDevice: (device) => {
    set({ selectedDevice: device });
  },

  connectDevice: async (deviceId: string) => {
    try {
      await deviceApi.connectDevice(deviceId);
      await get().fetchDevices();
      set({ success: 'Device connected successfully' });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to connect device' });
    }
  },

  disconnectDevice: async (deviceId: string) => {
    try {
      await deviceApi.disconnectDevice(deviceId);
      await get().fetchDevices();
      set({ success: 'Device disconnected successfully' });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to disconnect device' });
    }
  },

  connectTcpIp: async (ipPort: string) => {
    set({ connectingTcpIp: true, error: null, success: null });
    try {
      await deviceApi.connectTcpIp(ipPort);
      await get().fetchDevices();
      set({ connectingTcpIp: false, success: `Successfully connected to ${ipPort}` });
    } catch (error: any) {
      set({ connectingTcpIp: false, error: error.response?.data?.detail || 'Failed to connect via TCP/IP' });
    }
  },

  enableWireless: async (deviceId: string, port: number = 5555) => {
    // Guard: skip if device is already on tcpip
    const device = get().devices.find(d => d.device_id === deviceId);
    if (device?.connection_type === 'tcpip') {
      set({ success: '该设备已通过WiFi连接' });
      return;
    }
    set({ enablingWirelessDeviceId: deviceId, error: null, success: null });
    try {
      const response = await deviceApi.enableWireless(deviceId, port) as unknown as {
        success: boolean;
        message: string;
        device_id?: string;
      };

      if (response.success) {
        await get().fetchDevices();
        set({ enablingWirelessDeviceId: null, success: response.message });
      } else {
        set({ enablingWirelessDeviceId: null, error: response.message });
      }
    } catch (error: any) {
      set({
        enablingWirelessDeviceId: null,
        error: error.response?.data?.detail || 'Failed to enable wireless connection'
      });
    }
  },

  getDeviceIp: async (deviceId: string) => {
    try {
      const response = await deviceApi.getDeviceIp(deviceId) as unknown as { ip: string };
      return response.ip;
    } catch (error) {
      console.error('Failed to get device IP:', error);
      return null;
    }
  },

  clearMessages: () => {
    set({ error: null, success: null });
  },

  openDrawer: async (device: Device) => {
    set({ selectedDevice: device, drawerOpen: true, screenshotData: null, loadingScreenshot: true });
    try {
      const response = await deviceApi.getScreenshot(device.device_id) as unknown as { screenshot_base64: string };
      set({ screenshotData: response.screenshot_base64, loadingScreenshot: false });
    } catch {
      set({ screenshotData: null, loadingScreenshot: false });
    }
  },

  closeDrawer: () => {
    set({ drawerOpen: false, screenshotData: null });
  },
}));
