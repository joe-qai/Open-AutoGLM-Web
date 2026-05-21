import { useEffect, useState } from 'react';
import { ListTodo, Play, Square, Trash2, Clock, CheckCircle2, XCircle, Loader2, Plus, X, Bot, Upload, ChevronDown, ChevronUp } from 'lucide-react';
import { useTaskStore } from '../../stores/taskStore';
import { useAgentStore } from '../../stores/agentStore';
import { useDeviceStore } from '../../stores/deviceStore';
import { useApkStore } from '../../stores/apkStore';
import type { Script } from '../../stores/agentStore';

export function TaskPage() {
  const { tasks, fetchTasks, executeTask, stopTask, createTask, deleteTask } = useTaskStore();
  const { scripts } = useAgentStore();
  const { devices } = useDeviceStore();
  const { apks } = useApkStore();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [taskName, setTaskName] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [selectedScriptId, setSelectedScriptId] = useState('');
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([]);
  const [selectedApkId, setSelectedApkId] = useState('');
  const [expandedDevices, setExpandedDevices] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetchTasks();
  }, []);

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

  const handleCreateTask = async () => {
    if (!taskName || !selectedScriptId || selectedDeviceIds.length === 0) return;
    
    await createTask({
      name: taskName,
      description: taskDescription,
      script_id: selectedScriptId,
      device_id: selectedDeviceIds[0],
      apk_id: selectedApkId || undefined,
    });
    
    setIsModalOpen(false);
    setTaskName('');
    setTaskDescription('');
    setSelectedScriptId('');
    setSelectedDeviceIds([]);
    setSelectedApkId('');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'running':
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
      running: '执行中',
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
      case 'running':
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

      {/* Task Table */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-[#64748b] text-sm border-b border-[#334155]">
                <th className="text-left py-4 px-6 font-medium">任务名称</th>
                <th className="text-left py-4 px-6 font-medium">类型</th>
                <th className="text-left py-4 px-6 font-medium">执行设备</th>
                <th className="text-left py-4 px-6 font-medium">状态</th>
                <th className="text-left py-4 px-6 font-medium">进度</th>
                <th className="text-left py-4 px-6 font-medium">创建时间</th>
                <th className="text-left py-4 px-6 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const script = getScriptById(task.script_id);
                const primaryDevice = getDeviceInfo(task.device_id);
                const isExpanded = expandedDevices[task.task_id];
                
                return (
                  <>
                    <tr key={task.task_id} className="border-b border-[#334155] last:border-0 hover:bg-[#334155]/30">
                      <td className="py-4 px-6">
                        <div>
                          <p className="text-white font-medium">{task.name}</p>
                          <p className="text-[#64748b] text-sm">{task.description}</p>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        {script ? (
                          <span className="px-2 py-1 bg-[#334155] text-[#94a3b8] text-xs rounded flex items-center gap-1.5">
                            {getScriptTypeIcon(script)}
                            {script.name}
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-[#334155] text-[#94a3b8] text-xs rounded">
                            {task.task_type}
                          </span>
                        )}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <span className="text-[#94a3b8]">
                            {primaryDevice?.name || task.device_id || '-'}
                          </span>
                          <button
                            onClick={() => toggleDeviceExpand(task.task_id)}
                            className="text-[#64748b] hover:text-white transition-colors"
                          >
                            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                          </button>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(task.status)}
                          <span className={`text-sm ${getStatusClass(task.status)}`}>
                            {getStatusText(task.status)}
                          </span>
                        </div>
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-[#334155] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-indigo-500 rounded-full transition-all"
                              style={{ width: `${task.progress || 0}%` }}
                            />
                          </div>
                          <span className="text-[#94a3b8] text-sm">{task.progress || 0}%</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-[#94a3b8] text-sm">
                        {new Date(task.created_at).toLocaleString()}
                      </td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-2">
                          {task.status === 'running' ? (
                            <button
                              onClick={() => stopTask(task.task_id)}
                              className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                              title="中止"
                            >
                              <Square className="w-4 h-4" />
                            </button>
                          ) : (
                            <button
                              onClick={() => executeTask(task.task_id)}
                              className="p-2 text-green-400 hover:bg-green-500/20 rounded-lg transition-colors"
                              title="执行"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          <button
                            onClick={() => {
                              if (confirm('确定要删除此任务吗？')) {
                                deleteTask(task.task_id);
                              }
                            }}
                            className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                            title="删除"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="border-b border-[#334155] bg-[#0f172a]/30">
                        <td colSpan={7} className="py-3 px-6">
                          <div className="flex flex-wrap gap-2">
                            {primaryDevice && (
                              <span className="px-3 py-1.5 bg-[#334155] text-[#94a3b8] text-xs rounded-full">
                                {primaryDevice.name} ({primaryDevice.platform})
                              </span>
                            )}
                            {task.devices && task.devices.length > 0 && task.devices.map(deviceId => {
                              const device = getDeviceInfo(deviceId);
                              if (device && device.device_id !== task.device_id) {
                                return (
                                  <span key={deviceId} className="px-3 py-1.5 bg-[#334155] text-[#94a3b8] text-xs rounded-full">
                                    {device.name} ({device.platform})
                                  </span>
                                );
                              }
                              return null;
                            })}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>

        {tasks.length === 0 && (
          <div className="text-center py-20">
            <ListTodo className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无任务</h3>
            <p className="text-[#64748b]">点击"新增任务"创建您的第一个任务</p>
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
                  placeholder="输入任务名称"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">任务描述</label>
                <textarea
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500 resize-none"
                  rows={3}
                  placeholder="输入任务描述"
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
                  {devices.map((device) => (
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
                      {device.status === 'connected' ? (
                        <span className="text-green-400 text-xs">在线</span>
                      ) : (
                        <span className="text-gray-400 text-xs">离线</span>
                      )}
                    </label>
                  ))}
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
    </div>
  );
}