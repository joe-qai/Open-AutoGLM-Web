import { useEffect, useState, useCallback } from 'react';
import { FileText, Search, Filter, RefreshCw, Trash2, AlertCircle, AlertTriangle, Info, Bug, Clock, ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from 'lucide-react';
import { logApi } from '../../services/api';

interface LogEntry {
  log_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  category: 'device' | 'script' | 'task' | 'agent' | 'system' | 'api';
  action: string;
  operator: 'user' | 'system' | 'agent';
  target_id?: string;
  target_name?: string;
  detail?: Record<string, unknown>;
  device_id?: string;
  script_id?: string;
  task_id?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  duration_ms?: number;
  error?: string;
  created_at: string;
}

interface LogSummary {
  total: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count: number;
  avg_response_time_ms?: number;
}

const PAGE_SIZE = 50;

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<LogSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);
  const [totalLogs, setTotalLogs] = useState(0);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchSummary = useCallback(async () => {
    try {
      const response = await logApi.getSummary() as unknown as LogSummary;
      setSummary(response);
      setTotalLogs(response.total);
    } catch (error) {
      console.error('Failed to fetch log summary:', error);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (currentPage - 1) * PAGE_SIZE;
      const params: Record<string, any> = { skip, limit: PAGE_SIZE };
      if (debouncedSearch) params.search = debouncedSearch;
      if (selectedLevel !== 'all') params.level = selectedLevel;
      if (selectedCategory !== 'all') params.category = selectedCategory;
      if (startTime) params.start_time = startTime;
      if (endTime) params.end_time = endTime;

      const response = await logApi.getLogs(params) as unknown as LogEntry[];
      setLogs(response);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, debouncedSearch, selectedLevel, selectedCategory, startTime, endTime]);

  // Fetch summary on mount
  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  // Re-fetch logs when filters change
  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // Reset to page 1 when filters change
  useEffect(() => { setCurrentPage(1); }, [debouncedSearch, selectedLevel, selectedCategory, startTime, endTime]);

  const handleClearLogs = async () => {
    if (!confirm('确定要清空所有日志吗？')) return;
    try {
      await logApi.clearLogs();
      setLogs([]);
      setSummary(null);
      setCurrentPage(1);
      fetchSummary();
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  };

  const totalPages = Math.ceil(totalLogs / PAGE_SIZE);

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error': return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'info': return <Info className="w-4 h-4 text-blue-400" />;
      case 'debug': return <Bug className="w-4 h-4 text-purple-400" />;
      default: return <Info className="w-4 h-4 text-gray-400" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'bg-red-500/20 text-red-400';
      case 'warning': return 'bg-yellow-500/20 text-yellow-400';
      case 'info': return 'bg-blue-500/20 text-blue-400';
      case 'debug': return 'bg-purple-500/20 text-purple-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const getCategoryLabel = (category: string) => {
    const map: Record<string, string> = { device: '设备操作', script: '脚本操作', task: '任务操作', agent: 'Agent操作', system: '系统', api: 'API请求' };
    return map[category] || category;
  };

  const formatTime = (ts: string) => new Date(ts).toLocaleString('zh-CN');

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-400" />
            日志管理
          </h1>
          <p className="text-[#94a3b8] mt-1">查看和管理系统日志记录</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { fetchSummary(); fetchLogs(); }} className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors">
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
          <button onClick={handleClearLogs} title="清空日志" className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center gap-2 transition-colors">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center"><FileText className="w-5 h-5 text-blue-400" /></div>
              <div><p className="text-[#64748b] text-sm">总日志数</p><p className="text-white text-xl font-bold">{summary.total}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center"><AlertCircle className="w-5 h-5 text-red-400" /></div>
              <div><p className="text-[#64748b] text-sm">错误</p><p className="text-white text-xl font-bold">{summary.error_count}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center"><AlertTriangle className="w-5 h-5 text-yellow-400" /></div>
              <div><p className="text-[#64748b] text-sm">警告</p><p className="text-white text-xl font-bold">{summary.warning_count}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center"><Clock className="w-5 h-5 text-green-400" /></div>
              <div><p className="text-[#64748b] text-sm">平均响应时间</p><p className="text-white text-xl font-bold">{summary.avg_response_time_ms?.toFixed(1) || '-'}ms</p></div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-[#94a3b8]" />
          <span className="text-[#94a3b8] text-sm">筛选条件</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[#94a3b8] text-sm mb-2">搜索日志</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
              <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500" placeholder="搜索日志内容..." />
            </div>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">日志级别</label>
            <select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500">
              <option value="all">全部</option><option value="error">错误</option><option value="warning">警告</option><option value="info">信息</option><option value="debug">调试</option>
            </select>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">日志类别</label>
            <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500">
              <option value="all">全部</option><option value="device">设备操作</option><option value="script">脚本操作</option><option value="task">任务操作</option><option value="agent">Agent操作</option><option value="system">系统</option><option value="api">API请求</option>
            </select>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">开始时间</label>
            <input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-3 text-white focus:outline-none focus:border-indigo-500" />
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">结束时间</label>
            <input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-3 text-white focus:outline-none focus:border-indigo-500" />
          </div>
        </div>
      </div>

      {/* Log List */}
      {loading ? (
        <div className="text-center py-20">
          <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-[#94a3b8]">加载中...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-20">
          <FileText className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无日志</h3>
          <p className="text-[#64748b]">没有符合条件的日志记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <div key={log.log_id} className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
              <div className="p-4 cursor-pointer hover:bg-[#0f172a]/50 transition-colors" onClick={() => setExpandedLog(expandedLog === log.log_id ? null : log.log_id)}>
                <div className="flex items-start gap-4">
                  <div className="mt-1">{getLevelIcon(log.level)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getLevelColor(log.level)}`}>{log.level.toUpperCase()}</span>
                      <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">{getCategoryLabel(log.category)}</span>
                      <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded text-xs">{log.action}</span>
                      {log.status_code && <span className={`px-2 py-0.5 rounded text-xs font-medium ${log.status_code >= 400 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>{log.status_code}</span>}
                      {log.duration_ms && <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">{log.duration_ms}ms</span>}
                    </div>
                    <p className="text-white mt-2 line-clamp-2">{log.action}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-[#64748b]">
                      <span>{formatTime(log.created_at)}</span>
                      {log.target_name && <span>目标: {log.target_name}</span>}
                      {log.device_id && <span>设备: {log.device_id}</span>}
                      {log.endpoint && <span>端点: {log.endpoint}</span>}
                    </div>
                  </div>
                  <button className="text-[#64748b] hover:text-white transition-colors">
                    {expandedLog === log.log_id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {expandedLog === log.log_id && (
                <div className="border-t border-[#334155] bg-[#0f172a]/30 p-4">
                  <div className="space-y-3">
                    {log.error && (<div><p className="text-[#94a3b8] text-sm mb-1">错误信息</p><p className="text-red-400 text-sm font-mono">{log.error}</p></div>)}
                    {log.target_name && (<div><p className="text-[#94a3b8] text-sm mb-1">目标名称</p><p className="text-white text-sm">{log.target_name}</p></div>)}
                    {log.target_id && (<div><p className="text-[#94a3b8] text-sm mb-1">目标ID</p><p className="text-white text-sm font-mono">{log.target_id}</p></div>)}
                    {log.endpoint && (<div><p className="text-[#94a3b8] text-sm mb-1">请求端点</p><p className="text-white text-sm font-mono">{log.method} {log.endpoint}</p></div>)}
                    {log.detail && Object.keys(log.detail).length > 0 && (
                      <div>
                        <p className="text-[#94a3b8] text-sm mb-1">详细信息</p>
                        <pre className="text-[#94a3b8] text-sm font-mono bg-[#0f172a] rounded-lg p-3 overflow-auto max-h-48">{JSON.stringify(log.detail, null, 2)}</pre>
                      </div>
                    )}
                    <div><p className="text-[#94a3b8] text-sm mb-1">日志ID</p><p className="text-white text-sm font-mono">{log.log_id}</p></div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 px-4">
          <p className="text-[#94a3b8] text-sm">第 {currentPage} 页 / 共 {totalPages} 页 ({totalLogs} 条日志)</p>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-3 py-1.5 bg-[#334155] hover:bg-[#475569] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-1 transition-colors">
              <ChevronLeft className="w-4 h-4" />上一页
            </button>
            <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-3 py-1.5 bg-[#334155] hover:bg-[#475569] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-1 transition-colors">
              下一页<ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}