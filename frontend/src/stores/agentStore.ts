import { create } from 'zustand';
import { scriptApi, taskApi } from '../services/api';

export interface Script {
  script_id: string;
  name: string;
  description: string;
  platform: 'android' | 'ios' | 'harmonyos';
  script_type: 'ai_generated' | 'external';
  content: string;
  status: 'draft' | 'saved' | 'executed';
  created_at: string;
  updated_at?: string;
  version: number;
}

interface AgentState {
  scripts: Script[];
  currentScript: Script | null;
  isGenerating: boolean;
  isExecuting: boolean;
  isUploading: boolean;
  logs: string[];
  error: string | null;
  currentTaskId: string | null;
  executionMode: 'script' | 'direct'; // 脚本模式 vs 直接执行模式

  // Actions
  fetchScripts: () => Promise<void>;
  createScript: (data: {
    name: string;
    description: string;
    platform: string;
  }) => Promise<string | null>;
  uploadScript: (formData: FormData) => Promise<void>;
  generateScript: (data: {
    task_description: string;
    platform: string;
    device_id?: string;
  }) => Promise<string | null>;
  updateScript: (scriptId: string, content: string) => Promise<void>;
  executeScript: (scriptId: string, deviceId?: string, modelConfigId?: string) => Promise<void>;
  executeDirect: (data: {
    task_description: string;
    device_id?: string;
    platform?: string;
    max_steps?: number;
    mode?: string;
  }) => Promise<string | null>;
  setCurrentScript: (script: Script | null) => void;
  setExecutionMode: (mode: 'script' | 'direct') => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
}

export const useAgentStore = create<AgentState>((set, get) => ({
  scripts: [],
  currentScript: null,
  isGenerating: false,
  isExecuting: false,
  isUploading: false,
  logs: [],
  error: null,

  fetchScripts: async () => {
    try {
      const response = await scriptApi.getScripts() as unknown as { scripts: Script[] };
      set({ scripts: response.scripts });
    } catch (error) {
      set({ error: 'Failed to fetch scripts' });
    }
  },

  createScript: async (data) => {
    try {
      const response = await scriptApi.createScript(data) as unknown as { script_id: string };
      await get().fetchScripts();
      return response.script_id;
    } catch (error) {
      set({ error: 'Failed to create script' });
      return null;
    }
  },

  generateScript: async (data) => {
    set({ isGenerating: true, error: null });
    try {
      const response = await scriptApi.generateScript(data) as unknown as { script_id: string };
      await get().fetchScripts();
      set({ isGenerating: false });
      return response.script_id;
    } catch (error) {
      set({ error: 'Failed to generate script', isGenerating: false });
      return null;
    }
  },

  updateScript: async (scriptId: string, content: string) => {
    try {
      await scriptApi.updateScript(scriptId, { content });
      await get().fetchScripts();
    } catch (error) {
      set({ error: 'Failed to update script' });
    }
  },

  uploadScript: async (formData: FormData) => {
    set({ isUploading: true, error: null });
    try {
      await scriptApi.uploadScript(formData);
      await get().fetchScripts();
      set({ isUploading: false });
    } catch (error) {
      set({ error: 'Failed to upload script', isUploading: false });
    }
  },

  executeScript: async (scriptId: string, deviceId?: string, modelConfigId?: string) => {
    set({ isExecuting: true, error: null });
    try {
      await scriptApi.executeScript(scriptId, deviceId, modelConfigId);
      set({ isExecuting: false });
    } catch (error) {
      set({ error: 'Failed to execute script', isExecuting: false });
    }
  },

  executeDirect: async (data) => {
    set({ isExecuting: true, error: null });
    try {
      const response = await taskApi.executeNaturalLanguageTask(data) as unknown as { task_id: string };
      set({ isExecuting: false, currentTaskId: response.task_id });
      return response.task_id;
    } catch (error) {
      set({ error: 'Failed to execute task', isExecuting: false });
      return null;
    }
  },

  setCurrentScript: (script) => {
    set({ currentScript: script });
  },

  setExecutionMode: (mode) => {
    set({ executionMode: mode });
  },

  addLog: (log) => {
    set((state) => ({ logs: [...state.logs, log] }));
  },

  clearLogs: () => {
    set({ logs: [] });
  },
}));
