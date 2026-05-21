import { create } from 'zustand';
import { reportApi } from '../services/api';

export interface Report {
  report_id: string;
  name: string;
  task_id: string;
  task_name: string;
  platform: 'android' | 'ios' | 'harmonyos';
  status: 'pending' | 'running' | 'completed' | 'failed';
  duration?: number;
  created_at: string;
  updated_at?: string;
}

interface ReportState {
  reports: Report[];
  loading: boolean;
  error: string | null;

  // Actions
  fetchReports: () => Promise<void>;
  downloadReport: (reportId: string) => Promise<void>;
  deleteReport: (reportId: string) => Promise<void>;
}

export const useReportStore = create<ReportState>((set, get) => ({
  reports: [],
  loading: false,
  error: null,

  fetchReports: async () => {
    set({ loading: true, error: null });
    try {
      const response = await reportApi.getReports();
      // Backend returns List[ReportInfo] directly (not wrapped in { reports: [...] })
      const reportsData = Array.isArray(response) ? response : (response as any)?.reports || [];
      set({ reports: reportsData as Report[], loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch reports', loading: false });
    }
  },

  downloadReport: async (reportId: string) => {
    try {
      const response = await reportApi.downloadReport(reportId, 'html');
      
      // 创建下载链接
      const blob = new Blob([response.data], { type: 'text/html' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${reportId}.html`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      set({ error: 'Failed to download report' });
    }
  },

  deleteReport: async (reportId: string) => {
    try {
      await reportApi.deleteReport(reportId);
      await get().fetchReports();
    } catch (error) {
      set({ error: 'Failed to delete report' });
    }
  },
}));
