import { useEffect, useState, Fragment } from 'react';
import { ListTodo, Play, Square, CheckSquare, Trash2, Clock, CheckCircle2, XCircle, Loader2, Plus, X, Bot, Upload, FileText } from 'lucide-react';
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
      ? <Bot className="w-3 h-3 text-[#165DFF]" /> 
      : <Upload className="w-3 h-3 text-[#64748b]" />;
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
        return <CheckCircle2 className="w-4 h-4 text-[#22c55e]" />;
      case 'executing':
        return <Loader2 className="w-4 h-4 text-[#165DFF] animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-[#ef4444]" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-[#94a3b8]" />;
      case 'stopped':
        return <Square className="w-4 h-4 text-[#94a3b8]" />;
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
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <ListTodo className="w-5 h-5 text-[#165DFF]" />
            任务管理
          </h1>
          <p className="text-[#64748b] text-sm mt-1">查看和管理您的测试任务</p>
        </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white rounded-lg flex items-center gap-2 transition-colors duration-200"
          >
            <Plus className="w-4 h-4" />
            新增任务
          </button>
      </div>

      {selectedTaskIds.size > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between">
          <span className="text-[#165DFF] font-medium">已选择 {selectedTaskIds.size} 项</span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchDeleteClick}
              disabled={batchDeleting}
              title={batchDeleting ? '删除中' : '批量删除'}
              className="px-3 py-1.5 bg-[#ef4444] hover:bg-[#dc2626] disabled:opacity-50 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors duration-200"
            >
              {batchDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
              批量删除
            </button>
            <button
              onClick={() => setSelectedTaskIds(new Set())}
              className="px-3 py-1.5 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-xs font-medium rounded-lg flex items-center gap-1.5 transition-colors duration-200"
            >
              <X className="w-3.5 h-3.5" />
              取消选择
            </button>
          </div>
        </div>
      )}

      {/* Select All Header */}
      {tasks.length > 0 && (
        <div className="flex items-center gap-3 mb-3">
          <button onClick={toggleSelectAllTasks} className="text-[#64748b] hover:text-[#0f172a] transition-colors duration-200">
            {selectedTaskIds.size === tasks.length ? (
              <CheckSquare className="w-4 h-4 text-[#165DFF]" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
          <span className="text-[#64748b] text-xs">全选 ({tasks.length})</span>
        </div>
      )}

      {/* Task Cards */}
      <div className="space-y-3">
        {tasks.map((task) => {
          const script = getScriptById(task.script_id);
          const primaryDevice = getDeviceInfo(task.device_id);
          
          return (
            <Fragment key={task.task_id}>
              <div
                className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <button onClick={() => toggleTaskSelect(task.task_id)} className="mt-0.5 text-[#94a3b8] hover:text-[#165DFF] transition-colors duration-200">
                      {selectedTaskIds.has(task.task_id) ? (
                        <CheckSquare className="w-4 h-4 text-[#165DFF]" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                    <div>
                      <div className="flex items-center gap-2 mb-1.5">
                        <h3 className="text-[#0f172a] font-medium text-sm">{task.name}</h3>
                        <span className={`px-2.5 py-1 text-xs rounded-full ${
                          task.status === 'completed' ? 'bg-green-100 text-green-600' :
                          task.status === 'executing' ? 'bg-blue-100 text-blue-600' :
                          task.status === 'failed' ? 'bg-red-100 text-red-600' :
                          'bg-gray-100 text-gray-500'
                        }`}>
                          {getStatusText(task.status)}
                        </span>
                        {script && (
                          <span className="px-2.5 py-1 bg-[#f1f5f9] text-[#64748b] text-xs rounded-full flex items-center gap-1">
                            {getScriptTypeIcon(script)}
                            {script.name}
                          </span>
                        )}
                      </div>
                      <p className="text-[#64748b] text-xs">
                        {task.description || '暂无描述'} · {primaryDevice?.name || task.device_id || '-'} · {new Date(task.created_at).toLocaleString()}
                      </p>
                      {task.status === 'failed' && task.error_message && (
                        <p className="text-[#ef4444] text-xs mt-1.5 truncate" title={task.error_message}>
                          {task.error_message}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {task.status === 'executing' && (
                      <div className="mr-3">
                        <div className="flex items-center gap-1.5 text-xs text-[#64748b] mb-1">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>执行中</span>
                        </div>
                        <div className="w-40 h-1.5 bg-[#f1f5f9] rounded-full overflow-hidden">
                          <div className="h-full bg-[#165DFF] rounded-full" style={{ width: task.progress ? `${task.progress}%` : '50%' }} />
                        </div>
                      </div>
                    )}

                    <div className="flex items-center gap-1.5">
                      {task.status === 'executing' ? (
                        <button
                          onClick={() => handleStopTask(task.task_id)}
                          disabled={stoppingTaskId === task.task_id}
                          className="px-3 py-1.5 bg-[#ef4444] hover:bg-[#dc2626] disabled:opacity-50 text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                          title="中止"
                        >
                          {stoppingTaskId === task.task_id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Square className="w-3.5 h-3.5" />
                          )}
                          {stoppingTaskId === task.task_id ? '中止中' : '中止'}
                        </button>
                      ) : (
                        <button
                          onClick={() => executeTask(task.task_id)}
                          className="px-3 py-1.5 bg-[#22c55e] hover:bg-[#16a34a] text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                          title="执行"
                        >
                          <Play className="w-3.5 h-3.5" />
                          执行
                        </button>
                      )}
                      {task.status === 'completed' && (
                        <button
                          onClick={() => handlePreviewReport(task.task_id)}
                          className="px-3 py-1.5 bg-[#165DFF] hover:bg-[#0f4cdb] text-white text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                          title="查看报告"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          报告
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteClick(task.task_id)}
                        className="px-3 py-1.5 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-xs font-medium rounded-lg flex items-center gap-1.5 transition-all duration-200"
                        title="删除"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </Fragment>
          );
        })}

        {tasks.length === 0 && (
        <div className="text-center py-16 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg">
          <ListTodo className="w-12 h-12 text-[#94a3b8] mx-auto mb-3" />
          <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无任务</h3>
          <p className="text-[#64748b] text-sm">点击"新增任务"创建您的第一个任务</p>
        </div>
      )}
      </div>

      {/* Create Task Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto shadow-lg">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-[#0f172a]">创建任务</h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-colors duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">任务名称 *</label>
                <input
                  type="text"
                  value={taskName}
                  onChange={(e) => setTaskName(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  placeholder="请输入任务名称"
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">选择脚本 *</label>
                <select
                  value={selectedScriptId}
                  onChange={(e) => setSelectedScriptId(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
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
                <label className="block text-[#64748b] text-xs mb-1.5">选择设备 *</label>
                <div className="space-y-1.5">
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
                        className="w-3.5 h-3.5 rounded border-[#e2e8f0] bg-[#f8fafc] text-[#165DFF] focus:ring-[#165DFF]"
                      />
                      <span className="text-[#0f172a] text-sm">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-100 text-green-600 text-xs rounded-full">WiFi在线</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full">USB在线</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#94a3b8] text-sm">暂无在线设备</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">选择APK包 <span className="text-xs text-[#94a3b8]">(选填)</span></label>
                <select
                  value={selectedApkId}
                  onChange={(e) => setSelectedApkId(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                >
                  <option value="">不选择APK（设备已安装）</option>
                  {apks.map((apk) => (
                    <option key={apk.id} value={apk.id}>
                      {apk.name} {apk.version ? `(${apk.version})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex gap-2.5 pt-3">
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 px-3 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-sm font-medium rounded-lg transition-colors duration-200"
                >
                  取消
                </button>
                <button
                  onClick={handleCreateTask}
                  disabled={!taskName || !selectedScriptId || selectedDeviceIds.length === 0}
                  className="flex-1 px-3 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors duration-200"
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