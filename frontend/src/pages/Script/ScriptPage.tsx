import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileCode, Play, Edit, Trash2, Download, Bot, Upload, X, AlertCircle, CheckCircle } from 'lucide-react';
import { useAgentStore, type Script } from '../../stores/agentStore';
import { useTaskStore } from '../../stores/taskStore';
import { useDeviceStore } from '../../stores/deviceStore';
import { scriptApi } from '../../services/api';

export function ScriptPage() {
  const navigate = useNavigate();
  const { scripts, fetchScripts, uploadScript } = useAgentStore();
  const { createTask, executeTask } = useTaskStore();
  const { devices, fetchDevices } = useDeviceStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scriptName, setScriptName] = useState('');
  const [scriptDescription, setScriptDescription] = useState('');
  const [platform, setPlatform] = useState('android');
  const [editingScript, setEditingScript] = useState<Script | null>(null);
  const [editingContent, setEditingContent] = useState('');
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [selectedScriptForExec, setSelectedScriptForExec] = useState<Script | null>(null);
  const [isDeviceSelectOpen, setIsDeviceSelectOpen] = useState(false);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchScripts();
    fetchDevices();
  }, [fetchScripts, fetchDevices]);

  // Note: Removed old searchParams useEffect that navigated to /agent page.
  // Script execution now goes through task creation flow.

  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.endsWith('.py')) {
      setSelectedFile(file);
      setScriptName(file.name.replace('.py', ''));
    } else if (file) {
      setMessage({ type: 'error', text: '请选择Python文件(.py)' });
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('name', scriptName || selectedFile.name.replace('.py', ''));
    formData.append('description', scriptDescription);
    formData.append('platform', platform);
    
    try {
      await uploadScript(formData);
      setMessage({ type: 'success', text: '脚本上传成功' });
      setIsModalOpen(false);
      setSelectedFile(null);
      setScriptName('');
      setScriptDescription('');
      setPlatform('android');
    } catch (error) {
      setMessage({ type: 'error', text: '脚本上传失败' });
    }
  };

  const handleExecute = (script: Script) => {
    setSelectedScriptForExec(script);
    setSelectedDeviceId('');
    setIsDeviceSelectOpen(true);
  };

  const handleExecuteWithDevice = async () => {
    if (!selectedScriptForExec || !selectedDeviceId) return;

    const taskId = await createTask({
      name: `Execute: ${selectedScriptForExec.name}`,
      description: selectedScriptForExec.description || '',
      script_id: selectedScriptForExec.script_id,
      device_id: selectedDeviceId,
    });

    if (taskId) {
      await executeTask(taskId);
      navigate('/tasks');
    }

    setIsDeviceSelectOpen(false);
    setSelectedScriptForExec(null);
    setSelectedDeviceId('');
  };

  const handleEdit = (script: Script) => {
    setEditingScript(script);
    setEditingContent(script.content);
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingScript) return;
    
    try {
      await scriptApi.updateScript(editingScript.script_id, { content: editingContent });
      await fetchScripts();
      setMessage({ type: 'success', text: '脚本编辑成功' });
      setIsEditModalOpen(false);
      setEditingScript(null);
      setEditingContent('');
    } catch (error) {
      setMessage({ type: 'error', text: '脚本编辑失败' });
    }
  };

  const handleDownload = (script: Script) => {
    const blob = new Blob([script.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${script.name}.py`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage({ type: 'success', text: '脚本下载成功' });
  };

  const handleDelete = async (scriptId: string) => {
    if (!confirm('确定要删除这个脚本吗？')) return;
    
    try {
      await scriptApi.deleteScript(scriptId);
      await fetchScripts();
      setMessage({ type: 'success', text: '脚本删除成功' });
    } catch (error) {
      setMessage({ type: 'error', text: '脚本删除失败' });
    }
  };

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

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'ai_generated':
        return (
          <span className="px-2 py-1 bg-indigo-500/20 text-indigo-400 text-xs rounded flex items-center gap-1">
            <Bot className="w-3 h-3" />
            AI生成
          </span>
        );
      case 'external':
        return (
          <span className="px-2 py-1 bg-[#334155] text-[#94a3b8] text-xs rounded flex items-center gap-1">
            <Upload className="w-3 h-3" />
            本地上传
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Message */}
      {message && (
        <div className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${message.type === 'success' ? 'bg-green-900/30 border border-green-500/30 text-green-300' : 'bg-red-900/30 border border-red-500/30 text-red-300'}`}>
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileCode className="w-6 h-6 text-indigo-400" />
            脚本管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试脚本</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Upload className="w-4 h-4" />
            上传脚本
          </button>
        </div>
      </div>

      {/* Script Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scripts.map((script) => (
          <div
            key={script.script_id}
            className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 hover:border-[#475569] transition-colors"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#0f172a] rounded-lg flex items-center justify-center">
                  <FileCode className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-white font-medium">{script.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    {getPlatformIcon(script.platform)}
                    <span className="text-[#94a3b8] text-sm">{getPlatformText(script.platform)}</span>
                  </div>
                </div>
              </div>
              {getTypeBadge(script.script_type)}
            </div>

            <p className="text-[#64748b] text-sm mb-4 line-clamp-2">{script.description}</p>

            <div className="flex items-center justify-between text-xs text-[#64748b] mb-4">
              <span>版本 v{script.version}</span>
              <span>{new Date(script.created_at).toLocaleDateString()}</span>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleExecute(script)}
                className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Play className="w-4 h-4" />
                执行
              </button>
              <button
                onClick={() => handleEdit(script)}
                title="编辑"
                className="flex-1 py-2 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Edit className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleDownload(script)}
                className="p-2 text-[#94a3b8] hover:text-white hover:bg-[#334155] rounded-lg transition-colors"
                title="下载"
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleDelete(script.script_id)}
                className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {scripts.length === 0 && (
        <div className="text-center py-20">
          <FileCode className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无脚本</h3>
          <p className="text-[#64748b]">在Agent页面生成您的第一个脚本或上传本地脚本</p>
        </div>
      )}

      {/* Upload Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">上传本地脚本</h2>
              <button
                onClick={() => {
                  setIsModalOpen(false);
                  setSelectedFile(null);
                }}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择Python文件</label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".py"
                  onChange={handleFileChange}
                  className="hidden"
                  id="script-upload"
                />
                <label
                  htmlFor="script-upload"
                  className="w-full px-4 py-6 bg-[#0f172a] border-2 border-dashed border-[#334155] rounded-lg cursor-pointer hover:border-indigo-500 transition-colors flex flex-col items-center gap-2"
                >
                  <Upload className="w-8 h-8 text-[#64748b]" />
                  <span className="text-[#94a3b8] text-sm">点击选择 .py 文件</span>
                </label>
                {selectedFile && (
                  <p className="mt-2 text-green-400 text-sm">{selectedFile.name}</p>
                )}
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">脚本名称</label>
                <input
                  type="text"
                  value={scriptName}
                  onChange={(e) => setScriptName(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="输入脚本名称"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">脚本描述</label>
                <textarea
                  value={scriptDescription}
                  onChange={(e) => setScriptDescription(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500 resize-none"
                  rows={3}
                  placeholder="输入脚本描述"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">平台</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="android">Android</option>
                  <option value="ios">iOS</option>
                  <option value="harmonyos">HarmonyOS</option>
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => {
                    setIsModalOpen(false);
                    setSelectedFile(null);
                  }}
                  className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile}
                  className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  上传
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isEditModalOpen && editingScript && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">编辑脚本</h2>
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingScript(null);
                  setEditingContent('');
                }}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="flex-1 overflow-hidden">
              <textarea
                value={editingContent}
                onChange={(e) => setEditingContent(e.target.value)}
                className="w-full h-full min-h-[60vh] p-4 bg-[#0f172a] text-[#e2e8f0] font-mono text-sm resize-none focus:outline-none rounded-lg leading-relaxed"
                placeholder="输入脚本内容..."
                spellCheck={false}
              />
            </div>

            <div className="flex gap-3 mt-4">
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingScript(null);
                  setEditingContent('');
                }}
                className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSaveEdit}
                className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Device Select Modal for Script Execution */}
      {isDeviceSelectOpen && selectedScriptForExec && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">执行脚本: {selectedScriptForExec.name}</h2>
              <button
                onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">选择设备 *</label>
                <div className="space-y-2">
                  {devices.filter(d => d.status === 'connected').map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="device-select"
                        checked={selectedDeviceId === device.device_id}
                        onChange={() => setSelectedDeviceId(device.device_id)}
                        className="w-4 h-4 border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[#94a3b8]">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">WiFi</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">USB</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#64748b] text-sm">暂无在线设备，请先在设备管理页连接设备</p>
                  )}
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                  className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleExecuteWithDevice}
                  disabled={!selectedDeviceId}
                  className="flex-1 px-4 py-2.5 bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                >
                  创建任务并执行
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}