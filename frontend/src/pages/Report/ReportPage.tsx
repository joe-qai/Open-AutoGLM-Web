import { useEffect, useState } from 'react';
import { FileText, Download, Trash2, Clock, CheckCircle2, XCircle, Loader2, Calendar, CheckSquare, Square, X } from 'lucide-react';
import { useReportStore } from '../../stores/reportStore';
import type { Report } from '../../stores/reportStore';
import { ConfirmDialog } from '../../components/ConfirmDialog';

export function ReportPage() {
  const { reports, fetchReports, deleteReport, downloadReport, batchDeleteReports } = useReportStore();
  const [loadingReportId, setLoadingReportId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === reports.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(reports.map(r => r.report_id)));
    }
  };

  const handleBatchDelete = () => {
    setConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    setConfirmOpen(false);
    setBatchDeleting(true);
    try {
      await batchDeleteReports(Array.from(selectedIds));
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Batch delete failed:', error);
    } finally {
      setBatchDeleting(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'android':
        return <div className="w-2 h-2 rounded-full bg-[#3ddc84]" />;
      case 'ios':
        return <div className="w-2 h-2 rounded-full bg-white" />;
      case 'harmonyos':
        return <div className="w-2 h-2 rounded-full bg-[#007dff]" />;
      default:
        return null;
    }
  };

  const getPlatformText = (platform: string) => {
    const platformMap: Record<string, string> = {
      android: 'Android',
      ios: 'iOS',
      harmonyos: 'HarmonyOS',
    };
    return platformMap[platform] || platform;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'executing':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: '等待生成',
      executing: '生成中',
      completed: '已完成',
      failed: '生成失败',
    };
    return statusMap[status] || status;
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'executing':
        return 'text-blue-400';
      case 'failed':
        return 'text-red-400';
      default:
        return 'text-gray-400';
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins > 0) {
      return `${mins}分${secs}秒`;
    }
    return `${secs}秒`;
  };

  const handleDownload = async (report: Report) => {
    setLoadingReportId(report.report_id);
    try {
      await downloadReport(report.report_id);
    } finally {
      setLoadingReportId(null);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-400" />
            报告管理
          </h1>
          <p className="text-[#94a3b8] mt-1">查看和管理测试报告</p>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="mb-4 p-3 bg-indigo-900/30 border border-indigo-500/30 rounded-lg flex items-center justify-between">
          <span className="text-indigo-300 font-medium">已选择 {selectedIds.size} 项</span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchDelete}
              title={batchDeleting ? '删除中' : '批量删除'}
              className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              {batchDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-4 py-1.5 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <X className="w-4 h-4" />
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* Select All Header */}
      {reports.length > 0 && (
        <div className="flex items-center gap-4 mb-4">
          <button onClick={toggleSelectAll} className="text-slate-400 hover:text-white transition-colors">
            {selectedIds.size === reports.length ? (
              <CheckSquare className="w-5 h-5 text-indigo-400" />
            ) : (
              <Square className="w-5 h-5" />
            )}
          </button>
          <span className="text-slate-400 text-sm">全选 ({reports.length})</span>
        </div>
      )}

      {/* Report Cards */}
      <div className="space-y-4">
        {reports.map((report) => (
          <div
            key={report.report_id}
            className="bg-gradient-to-r from-slate-800/80 to-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 transition-all duration-300"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <button onClick={() => toggleSelect(report.report_id)} className="mt-1 text-slate-400 hover:text-white transition-colors">
                  {selectedIds.has(report.report_id) ? (
                    <CheckSquare className="w-5 h-5 text-indigo-400" />
                  ) : (
                    <Square className="w-5 h-5" />
                  )}
                </button>
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-white font-semibold text-lg">{report.name}</h3>
                    <span className={`px-3 py-1 text-xs rounded-full ${
                      report.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                      report.status === 'executing' ? 'bg-blue-500/20 text-blue-400' :
                      report.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                      'bg-slate-500/20 text-slate-400'
                    }`}>
                      {getStatusText(report.status)}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm">任务: {report.task_name} · {getPlatformText(report.platform)} · {new Date(report.created_at).toLocaleString()}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                {/* Stats */}
                <div className="flex items-center gap-6">
                  {report.total_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-2xl font-bold text-white">{report.total_cases}</p>
                      <p className="text-xs text-slate-400">总用例</p>
                    </div>
                  )}
                  {report.passed_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-400">{report.passed_cases}</p>
                      <p className="text-xs text-slate-400">通过</p>
                    </div>
                  )}
                  {report.failed_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-2xl font-bold text-red-400">{report.failed_cases}</p>
                      <p className="text-xs text-slate-400">失败</p>
                    </div>
                  )}
                  {report.pass_rate !== undefined && (
                    <div className="text-center">
                      <p className="text-2xl font-bold text-blue-400">{report.pass_rate}%</p>
                      <p className="text-xs text-slate-400">通过率</p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 ml-4 pl-4 border-l border-slate-700">
                  <button
                    onClick={() => handleDownload(report)}
                    disabled={loadingReportId === report.report_id || report.status !== 'completed'}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                    title="下载"
                  >
                    {loadingReportId === report.report_id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4" />
                    )}
                    下载报告
                  </button>
                  <button
                    onClick={() => deleteReport(report.report_id)}
                    className="px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                    title="删除"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}

        {reports.length === 0 && (
          <div className="text-center py-20 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm border border-slate-700/30 rounded-2xl">
            <FileText className="w-16 h-16 text-slate-500 mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无报告</h3>
            <p className="text-slate-400">执行任务后将自动生成报告</p>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="批量删除报告"
        message={`确定要删除 ${selectedIds.size} 个报告吗？此操作不可撤销。`}
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
