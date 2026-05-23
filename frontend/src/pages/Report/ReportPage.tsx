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
    await batchDeleteReports(Array.from(selectedIds));
    setSelectedIds(new Set());
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
              className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              批量删除
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

      {/* Report Table */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[#64748b] text-sm border-b border-[#334155]">
                <th className="text-left py-4 px-4 font-medium w-10">
                  <button onClick={toggleSelectAll} className="text-[#94a3b8] hover:text-white transition-colors">
                    {selectedIds.size === reports.length && reports.length > 0 ? (
                      <CheckSquare className="w-4 h-4" />
                    ) : (
                      <Square className="w-4 h-4" />
                    )}
                  </button>
                </th>
                <th className="text-left py-4 px-6 font-medium">报告名称</th>
                <th className="text-left py-4 px-6 font-medium">终端系统</th>
                <th className="text-left py-4 px-6 font-medium">执行时长</th>
                <th className="text-left py-4 px-6 font-medium">执行状态</th>
                <th className="text-left py-4 px-6 font-medium">创建时间</th>
                <th className="text-left py-4 px-6 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.report_id} className="border-b border-[#334155] last:border-0 hover:bg-[#334155]/30">
                  <td className="py-4 px-4">
                    <button onClick={() => toggleSelect(report.report_id)} className="text-[#94a3b8] hover:text-white transition-colors">
                      {selectedIds.has(report.report_id) ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-[#0f172a] rounded-lg flex items-center justify-center">
                        <FileText className="w-4 h-4 text-indigo-400" />
                      </div>
                      <div>
                        <p className="text-white font-medium">{report.name}</p>
                        <p className="text-[#64748b] text-sm">任务: {report.task_name}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      {getPlatformIcon(report.platform)}
                      <span className="text-[#94a3b8]">{getPlatformText(report.platform)}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-[#94a3b8]">
                    {report.duration !== undefined ? formatDuration(report.duration) : '-'}
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(report.status)}
                      <span className={`text-sm ${getStatusClass(report.status)}`}>
                        {getStatusText(report.status)}
                      </span>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-[#94a3b8] text-sm">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(report.created_at).toLocaleString()}
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDownload(report)}
                        disabled={loadingReportId === report.report_id || report.status !== 'completed'}
                        className="p-2 text-indigo-400 hover:bg-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                        title="下载"
                      >
                        {loadingReportId === report.report_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Download className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => deleteReport(report.report_id)}
                        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {reports.length === 0 && (
          <div className="text-center py-20">
            <FileText className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无报告</h3>
            <p className="text-[#64748b]">执行任务后将自动生成报告</p>
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
