import { create } from 'zustand';
import { taskApi } from '../services/api';

export interface Task {
  task_id: string;
  name: string;
  description: string;
  status: 'pending' | 'executing' | 'completed' | 'failed' | 'stopped';
  task_type: string;
  device_id: string;
  device_name?: string;
  script_id?: string;
  devices?: string[];
  progress: number;
  result?: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
}

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchTasks: () => Promise<void>;
  createTask: (data: {
    name: string;
    description: string;
    script_id: string;
    device_id: string;
    apk_id?: string;
  }) => Promise<string | null>;
  executeTask: (taskId: string) => Promise<void>;
  stopTask: (taskId: string) => Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  batchDeleteTasks: (taskIds: string[]) => Promise<void>;
  getTaskLogs: (taskId: string) => Promise<string[]>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  tasks: [],
  currentTask: null,
  loading: false,
  error: null,

  fetchTasks: async () => {
    set({ loading: true, error: null });
    try {
      const response = await taskApi.getTasks() as unknown as { tasks: Task[] };
      set({ tasks: response.tasks, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch tasks', loading: false });
    }
  },

  createTask: async (data) => {
    try {
      const requestData = {
        name: data.name,
        description: data.description,
        script_id: data.script_id,
        device_id: data.device_id,
        ...(data.apk_id && { apk_id: data.apk_id }),
      };
      const response = await taskApi.createTask(requestData) as unknown as { task_id: string };
      await get().fetchTasks();
      return response.task_id;
    } catch (error) {
      set({ error: 'Failed to create task' });
      return null;
    }
  },

  executeTask: async (taskId: string) => {
    try {
      await taskApi.executeTask(taskId);
      await get().fetchTasks();
    } catch (error) {
      set({ error: 'Failed to execute task' });
    }
  },

  stopTask: async (taskId: string) => {
    try {
      await taskApi.stopTask(taskId);
      await get().fetchTasks();
    } catch (error) {
      set({ error: 'Failed to stop task' });
    }
  },

  deleteTask: async (taskId: string) => {
    try {
      await taskApi.deleteTask(taskId);
      await get().fetchTasks();
    } catch (error) {
      set({ error: 'Failed to delete task' });
    }
  },

  batchDeleteTasks: async (taskIds: string[]) => {
    try {
      await taskApi.batchDeleteTasks(taskIds);
      await get().fetchTasks();
    } catch (error) {
      set({ error: 'Failed to batch delete tasks' });
    }
  },

  getTaskLogs: async (taskId: string) => {
    try {
      const response = await taskApi.getTaskLogs(taskId) as unknown as { logs: string[] };
      return response.logs;
    } catch (error) {
      return [];
    }
  },
}));
