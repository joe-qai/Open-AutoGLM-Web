import axios, { AxiosInstance, AxiosError } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// 创建axios实例
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加token等认证信息
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error: AxiosError) => {
    if (error.response) {
      // 服务器返回错误状态码
      console.error('API Error:', error.response.status, error.response.data);
    } else if (error.request) {
      // 请求发出但没有收到响应
      console.error('Network Error:', error.request);
    } else {
      // 请求配置出错
      console.error('Request Error:', error.message);
    }
    return Promise.reject(error);
  }
);

// 设备相关API
export const deviceApi = {
  getDevices: () => api.get('/api/v1/devices'),
  getDevice: (deviceId: string) => api.get(`/api/v1/devices/${deviceId}`),
  connectDevice: (deviceId: string) => api.post(`/api/v1/devices/${deviceId}/connect`),
  disconnectDevice: (deviceId: string) => api.post(`/api/v1/devices/${deviceId}/disconnect`),
  getScreenshot: (deviceId: string) => api.get(`/api/v1/devices/${deviceId}/screenshot`),
  launchApp: (deviceId: string, packageName: string) =>
    api.post(`/api/v1/devices/${deviceId}/launch`, { package_name: packageName }),
  connectTcpIp: (ipPort: string) => api.post('/api/v1/devices/tcpip/connect', { ip_port: ipPort }),
  disconnectTcpIp: (ipPort: string) => api.post(`/api/v1/devices/tcpip/disconnect/${ipPort}`),
  enableWireless: (deviceId: string, port: number = 5555) =>
    api.post(`/api/v1/devices/${deviceId}/wireless`, { port }),
  getDeviceIp: (deviceId: string) => api.get(`/api/v1/devices/${deviceId}/ip`),
};

// 任务相关API
export const taskApi = {
  getTasks: (params?: { skip?: number; limit?: number; status?: string }) =>
    api.get('/api/v1/tasks', { params }),
  getTask: (taskId: string) => api.get(`/api/v1/tasks/${taskId}`),
  createTask: (data: {
    name: string;
    description: string;
    script_id: string;
    device_id: string;
    apk_id?: string;
  }) => api.post('/api/v1/tasks', data),
  executeTask: (taskId: string) => api.post(`/api/v1/tasks/${taskId}/execute`),
  stopTask: (taskId: string) => api.post(`/api/v1/tasks/${taskId}/stop`),
  deleteTask: (taskId: string) => api.delete(`/api/v1/tasks/${taskId}`),
  getTaskLogs: (taskId: string) => api.get(`/api/v1/tasks/${taskId}/logs`),
};

// 脚本相关API
export const scriptApi = {
  getScripts: (params?: { skip?: number; limit?: number; script_type?: string }) =>
    api.get('/api/v1/scripts', { params }),
  getScript: (scriptId: string) => api.get(`/api/v1/scripts/${scriptId}`),
  createScript: (data: {
    name: string;
    description: string;
    platform: string;
    content?: string;
  }) => api.post('/api/v1/scripts', data),
  uploadScript: (formData: FormData) =>
    api.post('/api/v1/scripts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  updateScript: (scriptId: string, data: { content: string }) =>
    api.put(`/api/v1/scripts/${scriptId}`, data),
  generateScript: (data: {
    task_description: string;
    platform: string;
    device_id?: string;
  }) => api.post('/api/v1/scripts/generate', data),
  executeScript: (scriptId: string, deviceId?: string) =>
    api.post(`/api/v1/scripts/${scriptId}/execute`, { device_id: deviceId }),
  getScriptVersions: (scriptId: string) => api.get(`/api/v1/scripts/${scriptId}/versions`),
  deleteScript: (scriptId: string) => api.delete(`/api/v1/scripts/${scriptId}`),
};

// 报告相关API
export const reportApi = {
  getReports: (params?: { skip?: number; limit?: number; task_id?: string }) =>
    api.get('/api/v1/reports', { params }),
  getReport: (reportId: string) => api.get(`/api/v1/reports/${reportId}`),
  generateReport: (reportId: string) => api.post(`/api/v1/reports/${reportId}/generate`),
  downloadReport: (reportId: string, format: string = 'html') =>
    api.get(`/api/v1/reports/${reportId}/download`, { params: { format }, responseType: 'blob' }),
  deleteReport: (reportId: string) => api.delete(`/api/v1/reports/${reportId}`),
};

// APK相关API
export const apkApi = {
  getApks: () => api.get('/api/v1/apks'),
  getApk: (apkId: string) => api.get(`/api/v1/apks/${apkId}`),
  uploadApk: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/api/v1/apks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  deleteApk: (apkId: string) => api.delete(`/api/v1/apks/${apkId}`),
  installApk: (deviceId: string, apkId: string) =>
    api.post('/api/v1/apks/install', { device_id: deviceId, apk_id: apkId }),
};

// 项目相关API
export const projectApi = {
  getProjects: (params?: { skip?: number; limit?: number }) =>
    api.get('/api/v1/projects', { params }),
  getProject: (projectId: string) => api.get(`/api/v1/projects/${projectId}`),
  createProject: (data: {
    name: string;
    description: string;
    platform?: string;
  }) => api.post('/api/v1/projects', data),
  updateProject: (projectId: string, data: {
    name?: string;
    description?: string;
    platform?: string;
  }) => api.put(`/api/v1/projects/${projectId}`, data),
  deleteProject: (projectId: string) => api.delete(`/api/v1/projects/${projectId}`),
};

// 设置相关API
export const settingsApi = {
  getSettings: () => api.get('/api/v1/settings'),
  updateSettings: (data: Record<string, any>) => api.put('/api/v1/settings', data),
};

// 日志相关API
export const logApi = {
  getLogs: (params?: {
    level?: string;
    category?: string;
    device_id?: string;
    script_id?: string;
    task_id?: string;
    search?: string;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }) => api.get('/api/v1/logs', { params }),
  getSummary: () => api.get('/api/v1/logs/summary'),
  clearLogs: () => api.delete('/api/v1/logs'),
};

export default api;
