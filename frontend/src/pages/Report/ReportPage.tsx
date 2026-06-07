import { useEffect, useState } from 'react';
import { FileText, Download, Trash2, Clock, CheckCircle2, XCircle, Loader2, CheckSquare, Square, X } from 'lucide-react';
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
        return <CheckCircle2 className="w-4 h-4 text-[#22c55e]" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-[#ef4444]" />;
      case 'executing':
        return <Loader2 className="w-4 h-4 text-[#165DFF] animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-[#94a3b8]" />;
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
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#165DFF]" />
            报告管理
          </h1>
          <p className="text-[#64748b] text-sm mt-1">查看和管理测试报告</p>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
          <span className="text-[#165DFF] font-medium">已选择 {selectedIds.size} 项</span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchDelete}
              disabled={batchDeleting}
              title={batchDeleting ? '删除中' : '批量删除'}
              className="px-3 py-1.5 bg-[#ef4444] hover:bg-[#dc2626] disabled:opacity-50 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors duration-200"
            >
              {batchDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              批量删除
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-3 py-1.5 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors duration-200"
            >
              <X className="w-3.5 h-3.5" />
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* Select All Header */}
      {reports.length > 0 && (
        <div className="flex items-center gap-3 mb-3">
          <button onClick={toggleSelectAll} className="text-[#94a3b8] hover:text-[#165DFF] transition-colors duration-200">
            {selectedIds.size === reports.length ? (
              <CheckSquare className="w-4 h-4 text-[#165DFF]" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
          <span className="text-[#64748b] text-xs">全选 ({reports.length})</span>
        </div>
      )}

      {/* Report Cards */}
      <div className="space-y-3">
        {reports.map((report) => (
          <div
            key={report.report_id}
            className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3">
                <button onClick={() => toggleSelect(report.report_id)} className="mt-0.5 text-[#94a3b8] hover:text-[#165DFF] transition-colors duration-200">
                  {selectedIds.has(report.report_id) ? (
                    <CheckSquare className="w-4 h-4 text-[#165DFF]" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                </button>
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <h3 className="text-[#0f172a] font-medium text-sm">{report.name}</h3>
                    <span className={`px-2.5 py-1 text-xs rounded-full ${
                      report.status === 'completed' ? 'bg-green-100 text-green-600' :
                      report.status === 'executing' ? 'bg-blue-100 text-blue-600' :
                      report.status === 'failed' ? 'bg-red-100 text-red-600' :
                      'bg-gray-100 text-gray-500'
                    }`}>
                      {getStatusText(report.status)}
                    </span>
                  </div>
                  <p className="text-[#64748b] text-xs">任务: {report.task_name} · {getPlatformText(report.platform)} · {new Date(report.created_at).toLocaleString()}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                {/* Stats */}
                <div className="flex items-center gap-4">
                  {report.total_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-lg font-semibold text-[#0f172a]">{report.total_cases}</p>
                      <p className="text-xs text-[#94a3b8]">总用例</p>
                    </div>
                  )}
                  {report.passed_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-lg font-semibold text-[#22c55e]">{report.passed_cases}</p>
                      <p className="text-xs text-[#94a3b8]">通过</p>
                    </div>
                  )}
                  {report.failed_cases !== undefined && (
                    <div className="text-center">
                      <p className="text-lg font-semibold text-[#ef4444]">{report.failed_cases}</p>
                      <p className="text-xs text-[#94a3b8]">失败</p>
                    </div>
                  )}
                  {report.pass_rate !== undefined && (
                    <div className="text-center">
                      <p className="text-lg font-semibold text-[#165DFF]">{report.pass_rate}%</p>
                      <p className="text-xs text-[#94a3b8]">通过率</p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 ml-4 pl-4 border-l border-[#e2e8f0]">
                  <button
                    onClick={() => handleDownload(report)}
                    disabled={loadingReportId === report.report_id || report.status !== 'completed'}
                    className="px-3 py-1.5 bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                    title="下载"
                  >
                    {loadingReportId === report.report_id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Download className="w-3.5 h-3.5" />
                    )}
                    下载报告
                  </button>
                  <button
                    onClick={() => deleteReport(report.report_id)}
                    className="px-3 py-1.5 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                    title="删除"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}

        {reports.length === 0 && (
          <div className="text-center py-16 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg">
            <FileText className="w-12 h-12 text-[#94a3b8] mx-auto mb-3" />
            <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无报告</h3>
            <p className="text-[#64748b] text-sm">执行任务后将自动生成报告</p>
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
