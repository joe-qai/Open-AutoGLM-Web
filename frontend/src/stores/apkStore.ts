import { create } from 'zustand';
import { apkApi } from '../services/api';

export interface Apk {
  id: string;
  name: string;
  original_filename?: string;
  version?: string;
  package_name?: string;
  file_size?: number;
  upload_time: string;
  status: 'uploaded' | 'installed' | 'failed';
  file_path?: string;
  icon_base64?: string;
}

interface ApkState {
  apks: Apk[];
  loading: boolean;
  uploading: boolean;
  installing: boolean;
  error: string | null;
  success: string | null;

  // Actions
  fetchApks: () => Promise<void>;
  uploadApk: (file: File) => Promise<void>;
  deleteApk: (apkId: string) => Promise<void>;
  installApk: (deviceId: string, apkId: string) => Promise<void>;
  clearMessages: () => void;
}

export const useApkStore = create<ApkState>((set, get) => ({
  apks: [],
  loading: false,
  uploading: false,
  installing: false,
  error: null,
  success: null,

  fetchApks: async () => {
    set({ loading: true, error: null });
    try {
      const response = (await apkApi.getApks()) as unknown as { apks: Apk[] };
      set({ apks: response.apks || [], loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch APKs', loading: false });
    }
  },

  uploadApk: async (file: File) => {
    set({ uploading: true, error: null, success: null });
    try {
      const response = (await apkApi.uploadApk(file)) as unknown as { success: boolean; message: string; apk?: Apk };
      if (response.success) {
        set({ uploading: false, success: 'APK uploaded successfully' });
        await get().fetchApks();
      } else {
        set({ error: response.message, uploading: false });
      }
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to upload APK', uploading: false });
    }
  },

  deleteApk: async (apkId: string) => {
    try {
      await apkApi.deleteApk(apkId);
      set({ success: 'APK deleted successfully' });
      await get().fetchApks();
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to delete APK' });
    }
  },

  installApk: async (deviceId: string, apkId: string) => {
    set({ installing: true, error: null, success: null });
    try {
      await apkApi.installApk(deviceId, apkId);
      set({ installing: false, success: 'APK installed successfully' });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Failed to install APK', installing: false });
    }
  },

  clearMessages: () => {
    set({ error: null, success: null });
  },
}));
