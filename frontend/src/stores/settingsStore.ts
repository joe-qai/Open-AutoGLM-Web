import { create } from 'zustand';
import { settingsApi } from '../services/api';

export interface Settings {
  database: {
    path: string;
  };
  // 可以添加更多设置字段
}

interface SettingsState {
  settings: Settings | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSettings: (data: Partial<Settings>) => Promise<void>;
}

const defaultSettings: Settings = {
  database: {
    path: './data/agent_platform.db',
  },
};

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: defaultSettings,
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const response = await settingsApi.getSettings() as any;
      set({ settings: response || defaultSettings, loading: false });
    } catch (error) {
      // 如果API失败，使用默认设置
      set({ settings: defaultSettings, loading: false });
    }
  },

  updateSettings: async (data) => {
    set({ loading: true, error: null });
    try {
      const currentSettings = get().settings || defaultSettings;
      const mergedSettings = { ...currentSettings, ...data };
      await settingsApi.updateSettings(mergedSettings);
      set({ settings: mergedSettings, loading: false });
    } catch (error) {
      set({ error: 'Failed to update settings', loading: false });
    }
  },
}));
