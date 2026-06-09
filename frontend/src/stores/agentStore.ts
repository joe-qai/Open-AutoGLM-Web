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

export interface LogEntry {
  id: string;
  step: number;
  type: 'system' | 'think' | 'action' | 'success' | 'error' | 'warning';
  action?: string;
  thinking?: string;
  thinkingAction?: string;
  result?: string;
  screenshot?: string;  // base64 截图
  timestamp: Date;
}

interface AgentState {
  scripts: Script[];
  currentScript: Script | null;
  isGenerating: boolean;
  isExecuting: boolean;
  isUploading: boolean;
  logs: LogEntry[];
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
    save_task?: boolean;
  }) => Promise<string | null>;
  setCurrentScript: (script: Script | null) => void;
  setExecutionMode: (mode: 'script' | 'direct') => void;
  addLog: (log: string) => void;
  addStructuredLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
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
  currentTaskId: null,
  executionMode: 'direct',

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
      console.log('[AgentStore] executeDirect called with:', data);
      const response = await taskApi.executeNaturalLanguageTask(data);
      console.log('[AgentStore] API response:', response);
      const taskId = response?.task_id;
      console.log('[AgentStore] taskId:', taskId);
      set({ isExecuting: false, currentTaskId: taskId });
      return taskId || null;
    } catch (error: any) {
      console.error('[AgentStore] executeDirect error:', error);
      console.error('[AgentStore] error response:', error.response);
      console.error('[AgentStore] error message:', error.message);
      console.error('[AgentStore] error code:', error.code);
      set({ error: error.message || 'Failed to execute task', isExecuting: false });
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
    set((state) => ({ 
      logs: [...state.logs, {
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        step: 0,
        type: 'system' as const,
        result: log,
        timestamp: new Date(),
      }] 
    }));
  },

  addStructuredLog: (log) => {
    set((state) => ({ 
      logs: [...state.logs, {
        ...log,
        id: `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
      }] 
    }));
  },

  clearLogs: () => {
    set({ logs: [] });
  },
}));
