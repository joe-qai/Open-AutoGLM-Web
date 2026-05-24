import { create } from 'zustand';
import { projectApi } from '../services/api';

export interface Project {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  task_count?: number;
}

interface ProjectState {
  projects: Project[];
  selectedProject: Project | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchProjects: () => Promise<void>;
  selectProject: (project: Project | null) => void;
  createProject: (data: {
    name: string;
    description: string;
  }) => Promise<void>;
  updateProject: (projectId: string, data: {
    name?: string;
    description?: string;
  }) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  selectedProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const response = await projectApi.getProjects() as unknown as { projects: Project[] };
      set({ projects: response.projects, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch projects', loading: false });
    }
  },

  selectProject: (project) => {
    set({ selectedProject: project });
  },

  createProject: async (data) => {
    try {
      await projectApi.createProject(data);
      await get().fetchProjects();
    } catch (error) {
      set({ error: 'Failed to create project' });
    }
  },

  updateProject: async (projectId, data) => {
    try {
      await projectApi.updateProject(projectId, data);
      await get().fetchProjects();
    } catch (error) {
      set({ error: 'Failed to update project' });
    }
  },

  deleteProject: async (projectId) => {
    try {
      await projectApi.deleteProject(projectId);
      await get().fetchProjects();
    } catch (error) {
      set({ error: 'Failed to delete project' });
    }
  },
}));
