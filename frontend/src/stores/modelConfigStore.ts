import { create } from 'zustand';
import { modelConfigApi } from '../services/api';

export interface ModelConfig {
  config_id: string;
  name: string;
  provider: 'openai' | 'anthropic';
  base_url?: string;
  api_key: string;
  model_name: string;
  is_default: boolean;
  created_at: string;
  updated_at?: string;
}

interface ModelConfigState {
  configs: ModelConfig[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchConfigs: () => Promise<void>;
  createConfig: (data: Omit<ModelConfig, 'config_id' | 'created_at'>) => Promise<void>;
  updateConfig: (id: string, data: Partial<ModelConfig>) => Promise<void>;
  deleteConfig: (id: string) => Promise<void>;
}

export const useModelConfigStore = create<ModelConfigState>((set, get) => ({
  configs: [],
  loading: false,
  error: null,

  fetchConfigs: async () => {
    set({ loading: true, error: null });
    try {
      const response = await modelConfigApi.getConfigs();
      const data = response as unknown;
      const configs = (data as { configs?: ModelConfig[] }).configs || (data as ModelConfig[]);
      set({ configs, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch model configurations', loading: false });
    }
  },

  createConfig: async (data) => {
    set({ loading: true, error: null });
    try {
      await modelConfigApi.createConfig(data);
      await get().fetchConfigs();
    } catch (error) {
      set({ error: 'Failed to create model configuration', loading: false });
      throw error;
    }
  },

  updateConfig: async (id, data) => {
    set({ loading: true, error: null });
    try {
      await modelConfigApi.updateConfig(id, data);
      await get().fetchConfigs();
    } catch (error) {
      set({ error: 'Failed to update model configuration', loading: false });
      throw error;
    }
  },

  deleteConfig: async (id) => {
    set({ loading: true, error: null });
    try {
      await modelConfigApi.deleteConfig(id);
      await get().fetchConfigs();
    } catch (error) {
      set({ error: 'Failed to delete model configuration', loading: false });
      throw error;
    }
  },
}));
