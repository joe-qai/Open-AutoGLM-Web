import { useEffect, useState, Fragment } from 'react';
import { ListTodo, Play, Square, CheckSquare, Trash2, Clock, CheckCircle2, XCircle, Loader2, Plus, X, Bot, Upload, ChevronDown, ChevronUp, FileText, AlertTriangle } from 'lucide-react';
import { useTaskStore } from '../../stores/taskStore';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { ToastManager, ToastType } from '../../components/Toast';
import { useAgentStore } from '../../stores/agentStore';
import { useDeviceStore } from '../../stores/deviceStore';
import { useApkStore } from '../../stores/apkStore';
import type { Script } from '../../stores/agentStore';

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

export function TaskPage() {
  const { tasks, fetchTasks, executeTask, stopTask, createTask, deleteTask } = useTaskStore();
  const { scripts, fetchScripts } = useAgentStore();
  const { devices, fetchDevices } = useDeviceStore();
  const { apks, fetchApks } = useApkStore();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [taskName, setTaskName] = useState('');
  const [selectedScriptId, setSelectedScriptId] = useState('');
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([]);
  const [selectedApkId, setSelectedApkId] = useState('');
  const [expandedDevices, setExpandedDevices] = useState<Record<string, boolean>>({});
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [batchDeleting, setBatchDeleting] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [stoppingTaskId, setStoppingTaskId] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
    fetchScripts();
    fetchDevices();
    fetchApks();
  }, []);

  useEffect(() => {
    const hasExecuting = tasks.some(t => t.status === 'executing');
    if (!hasExecuting) return;
    const interval = setInterval(() => fetchTasks(), 5000);
    return () => clearInterval(interval);
  }, [tasks, fetchTasks]);

  const getScriptById = (scriptId: string | undefined): Script | undefined => {
    return scripts.find(s => s.script_id === scriptId);
  };

  const getScriptTypeLabel = (script: Script) => {
    return script.script_type === 'ai_generated' ? 'AI生成' : '本地上传';
  };

  const getScriptTypeIcon = (script: Script) => {
    return script.script_type === 'ai_generated' 
      ? <Bot className="w-3 h-3 text-indigo-400" /> 
      : <Upload className="w-3 h-3 text-[#94a3b8]" />;
  };

  const addToast = (message: string, type: ToastType = 'info') => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleCreateTask = async () => {
    if (!taskName || !selectedScriptId || selectedDeviceIds.length === 0) return;

    const taskId = await createTask({
      name: taskName,
      description: '',
      script_id: selectedScriptId,
      device_id: selectedDeviceIds[0],
      apk_id: selectedApkId || undefined,
    });

    if (taskId) {
      setIsModalOpen(false);
      setTaskName('');
      setSelectedScriptId('');
      setSelectedDeviceIds([]);
      setSelectedApkId('');
      addToast('任务创建成功', 'success');
    }
  };

  const handlePreviewReport = (taskId: string) => {
    window.open(`/api/v1/reports/${taskId}/preview`, '_blank');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'executing':
        return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-400" />;
      case 'stopped':
        return <Square className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      pending: '准备中',
      executing: '执行中',
      completed: '成功',
      failed: '失败',
      stopped: '已停止',
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
      case 'stopped':
        return 'text-gray-400';
      default:
        return 'text-gray-400';
    }
  };

  const toggleDeviceExpand = (taskId: string) => {
    setExpandedDevices(prev => ({
      ...prev,
      [taskId]: !prev[taskId]
    }));
  };

  const getDeviceInfo = (deviceId: string | undefined) => {
    return devices.find(d => d.device_id === deviceId);
  };

  const toggleTaskSelect = (id: string) => {
    setSelectedTaskIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAllTasks = () => {
    if (selectedTaskIds.size === tasks.length) {
      setSelectedTaskIds(new Set());
    } else {
      setSelectedTaskIds(new Set(tasks.map(t => t.task_id)));
    }
  };

  const handleBatchDeleteClick = () => {
    setConfirmOpen(true);
  };

  const handleStopTask = async (taskId: string) => {
    setStoppingTaskId(taskId);
    try {
      await stopTask(taskId);
      addToast('任务已中止', 'info');
    } catch (error) {
      console.error('Failed to stop task:', error);
      addToast('中止任务失败', 'error');
    } finally {
      setStoppingTaskId(null);
    }
  };

  const handleDeleteClick = (taskId: string) => {
    setTaskToDelete(taskId);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!taskToDelete) return;
    setDeleteConfirmOpen(false);
    try {
      await deleteTask(taskToDelete);
      addToast('任务删除成功', 'success');
    } catch (error) {
      console.error('Failed to delete task:', error);
      addToast('删除任务失败', 'error');
    } finally {
      setTaskToDelete(null);
    }
  };

  const handleConfirmBatchDelete = async () => {
    setConfirmOpen(false);
    setBatchDeleting(true);
    try {
      await useTaskStore.getState().batchDeleteTasks(Array.from(selectedTaskIds));
      setSelectedTaskIds(new Set());
      addToast(`成功删除 ${selectedTaskIds.size} 个任务`, 'success');
    } catch (error) {
      console.error('Batch delete failed:', error);
      addToast('批量删除失败', 'error');
    } finally {
      setBatchDeleting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ListTodo className="w-6 h-6 text-indigo-400" />
            任务管理
          </h1>
          <p className="text-[#94a3b8] mt-1">查看和管理您的测试任务</p>
        </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            新增任务
          </button>
      </div>

      {selectedTaskIds.size > 0 && (
        <div className="mb-4 p-3 bg-indigo-900/30 border border-indigo-500/30 rounded-lg flex items-center justify-between">
          <span className="text-indigo-300 font-medium">已选择 {selectedTaskIds.size} 项</span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchDeleteClick}
              disabled={batchDeleting}
              title={batchDeleting ? '删除中' : '批量删除'}
              className="px-4 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-red-800 text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              {batchDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
            </button>
            <button
              onClick={() => setSelectedTaskIds(new Set())}
              className="px-4 py-1.5 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <X className="w-4 h-4" />
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* Select All Header */}
      {tasks.length > 0 && (
        <div className="flex items-center gap-4 mb-4">
          <button onClick={toggleSelectAllTasks} className="text-slate-400 hover:text-white transition-colors">
            {selectedTaskIds.size === tasks.length ? (
              <CheckSquare className="w-5 h-5 text-indigo-400" />
            ) : (
              <Square className="w-5 h-5" />
            )}
          </button>
          <span className="text-slate-400 text-sm">全选 ({tasks.length})</span>
        </div>
      )}

      {/* Task Cards */}
      <div className="space-y-4">
        {tasks.map((task) => {
          const script = getScriptById(task.script_id);
          const primaryDevice = getDeviceInfo(task.device_id);
          const isExpanded = expandedDevices[task.task_id];
          
          return (
            <Fragment key={task.task_id}>
              <div
                className="bg-gradient-to-r from-slate-800/80 to-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 transition-all duration-300"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <button onClick={() => toggleTaskSelect(task.task_id)} className="mt-1 text-slate-400 hover:text-white transition-colors">
                      {selectedTaskIds.has(task.task_id) ? (
                        <CheckSquare className="w-5 h-5 text-indigo-400" />
                      ) : (
                        <Square className="w-5 h-5" />
                      )}
                    </button>
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-white font-semibold text-lg">{task.name}</h3>
                        <span className={`px-3 py-1 text-xs rounded-full ${
                          task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                          task.status === 'executing' ? 'bg-blue-500/20 text-blue-400' :
                          task.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-500/20 text-slate-400'
                        }`}>
                          {getStatusText(task.status)}
                        </span>
                        {script && (
                          <span className="px-3 py-1 bg-slate-700/50 text-slate-300 text-xs rounded-full flex items-center gap-1.5">
                            {getScriptTypeIcon(script)}
                            {script.name}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-400 text-sm">
                        {task.description || '暂无描述'} · {primaryDevice?.name || task.device_id || '-'} · {new Date(task.created_at).toLocaleString()}
                      </p>
                      {task.status === 'failed' && task.error_message && (
                        <p className="text-red-400 text-xs mt-2 truncate" title={task.error_message}>
                          {task.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {/* Progress bar if executing */}
                    {task.status === 'executing' && (
                      <div className="mr-4">
                        <div className="flex items-center gap-2 text-sm text-slate-400 mb-1">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span>执行中</span>
                        </div>
                        <div className="w-48 h-2 bg-slate-700 rounded-full overflow-hidden">
                          <div className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full animate-pulse" style={{ width: task.progress ? `${task.progress}%` : '50%' }} />
                        </div>
                      </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {task.status === 'executing' ? (
                        <button
                          onClick={() => handleStopTask(task.task_id)}
                          disabled={stoppingTaskId === task.task_id}
                          className="px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                          title="中止"
                        >
                          {stoppingTaskId === task.task_id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                          {stoppingTaskId === task.task_id ? '中止中...' : '中止'}
                        </button>
                      ) : (
                        <button
                          onClick={() => executeTask(task.task_id)}
                          className="px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                          title="执行"
                        >
                          <Play className="w-4 h-4" />
                          执行
                        </button>
                      )}
                      {task.status === 'completed' && (
                        <button
                          onClick={() => handlePreviewReport(task.task_id)}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                          title="查看报告"
                        >
                          <FileText className="w-4 h-4" />
                          报告
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteClick(task.task_id)}
                        className="px-4 py-2 bg-slate-700/50 hover:bg-slate-600/50 text-white text-sm font-medium rounded-xl flex items-center gap-2 transition-all duration-200"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Expanded devices */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-700/50">
                    <div className="flex flex-wrap gap-2">
                      {primaryDevice && (
                        <span className="px-3 py-1.5 bg-slate-700/50 text-slate-300 text-xs rounded-full">
                          {primaryDevice.name} ({primaryDevice.platform})
                        </span>
                      )}
                      {task.devices && task.devices.length > 0 && task.devices.map(deviceId => {
                        const device = getDeviceInfo(deviceId);
                        if (device && device.device_id !== task.device_id) {
                          return (
                            <span key={deviceId} className="px-3 py-1.5 bg-slate-700/50 text-slate-300 text-xs rounded-full">
                              {device.name} ({device.platform})
                            </span>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </div>
                )}
              </div>
            </Fragment>
          );
        })}

        {tasks.length === 0 && (
          <div className="text-center py-20 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm border border-slate-700/30 rounded-2xl">
            <ListTodo className="w-16 h-16 text-slate-500 mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无任务</h3>
            <p className="text-slate-400">点击"新增任务"创建您的第一个任务</p>
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">创建任务</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">任务名称 *</label>
                <input
                  type="text"
                  value={taskName}
                  onChange={(e) => setTaskName(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="请输入任务名称"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择脚本 *</label>
                <select
                  value={selectedScriptId}
                  onChange={(e) => setSelectedScriptId(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">请选择脚本</option>
                  {scripts.map((script) => (
                    <option key={script.script_id} value={script.script_id}>
                      {script.name} ({getScriptTypeLabel(script)})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择设备 *</label>
                <div className="space-y-2">
                  {devices.filter(d => d.status === 'connected').map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedDeviceIds.includes(device.device_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDeviceIds([...selectedDeviceIds, device.device_id]);
                          } else {
                            setSelectedDeviceIds(selectedDeviceIds.filter(id => id !== device.device_id));
                          }
                        }}
                        className="w-4 h-4 rounded border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[#94a3b8]">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">WiFi在线</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">USB在线</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#64748b] text-sm">暂无在线设备</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择APK包 <span className="text-xs text-[#64748b]">(选填)</span></label>
                <select
                  value={selectedApkId}
                  onChange={(e) => setSelectedApkId(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">不选择APK（设备已安装）</option>
                  {apks.map((apk) => (
                    <option key={apk.id} value={apk.id}>
                      {apk.name} {apk.version ? `(${apk.version})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateTask}
                  disabled={!taskName || !selectedScriptId || selectedDeviceIds.length === 0}
                  className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  创建任务
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmOpen}
        title="批量删除任务"
        message={`确定要删除 ${selectedTaskIds.size} 个任务吗？关联的报告也将被删除，此操作不可撤销。`}
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleConfirmBatchDelete}
        onCancel={() => setConfirmOpen(false)}
      />

      <ConfirmDialog
        open={deleteConfirmOpen}
        title="删除任务"
        message="确定要删除此任务吗？关联的报告也将被删除，此操作不可撤销。"
        confirmLabel="删除"
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteConfirmOpen(false)}
      />

      <ToastManager toasts={toasts} removeToast={removeToast} />
    </div>
  );
}