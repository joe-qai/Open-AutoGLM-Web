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
          <span className="px-2 py-1 bg-blue-50 text-[#165DFF] text-xs rounded-full flex items-center gap-1">
            <Bot className="w-3 h-3" />
            AI生成
          </span>
        );
      case 'external':
        return (
          <span className="px-2 py-1 bg-[#f1f5f9] text-[#64748b] text-xs rounded-full flex items-center gap-1">
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
        <div className={`mb-4 p-3 rounded-lg flex items-center gap-2 ${message.type === 'success' ? 'bg-green-50 border border-green-200 text-green-600' : 'bg-red-50 border border-red-200 text-red-600'}`}>
          {message.type === 'success' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          {message.text}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <FileCode className="w-5 h-5 text-[#165DFF]" />
            脚本管理
          </h1>
          <p className="text-[#64748b] text-sm mt-1">管理您的测试脚本</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setIsModalOpen(true)}
            className="px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white rounded-lg flex items-center gap-2 transition-colors duration-200"
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
            className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 bg-gradient-to-br from-amber-100 to-orange-100 rounded-lg flex items-center justify-center shrink-0 border border-amber-200">
                  <FileCode className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <h3 className="text-[#0f172a] font-medium text-sm">{script.name}</h3>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {getPlatformIcon(script.platform)}
                    <span className="text-[#64748b] text-xs">{getPlatformText(script.platform)}</span>
                  </div>
                </div>
              </div>
              {getTypeBadge(script.script_type)}
            </div>

            <p className="text-[#64748b] text-xs mb-3 line-clamp-2">{script.description || '暂无描述'}</p>

            <div className="flex items-center justify-between text-xs text-[#94a3b8] mb-3">
              <span>版本 v{script.version}</span>
              <span>{new Date(script.created_at).toLocaleDateString()}</span>
            </div>

            <div className="flex gap-1.5">
              <button
                onClick={() => handleExecute(script)}
                className="flex-1 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-all duration-200"
              >
                <Play className="w-3.5 h-3.5" />
                执行
              </button>
              <button
                onClick={() => handleEdit(script)}
                title="编辑"
                className="flex-1 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-all duration-200"
              >
                <Edit className="w-3.5 h-3.5" />
                编辑
              </button>
              <button
                onClick={() => handleDownload(script)}
                className="p-2 bg-[#f8fafc] hover:bg-[#f1f5f9] text-[#64748b] rounded-lg transition-all duration-200"
                title="下载"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => handleDelete(script.script_id)}
                className="p-2 bg-[#f8fafc] hover:bg-[#fef2f2] text-[#64748b] hover:text-[#ef4444] rounded-lg transition-all duration-200"
                title="删除"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {scripts.length === 0 && (
        <div className="text-center py-16 bg-[#f8fafc] border border-[#e2e8f0] rounded-lg">
          <FileCode className="w-12 h-12 text-[#94a3b8] mx-auto mb-3" />
          <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无脚本</h3>
          <p className="text-[#64748b] text-sm">在AI Agent页面生成您的第一个脚本或上传本地脚本</p>
        </div>
      )}

      {/* Upload Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 w-full max-w-md mx-4 shadow-lg">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-[#0f172a]">上传本地脚本</h2>
              <button
                onClick={() => {
                  setIsModalOpen(false);
                  setSelectedFile(null);
                }}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-colors duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">选择Python文件</label>
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
                  className="w-full px-4 py-5 bg-[#f8fafc] border-2 border-dashed border-[#e2e8f0] rounded-lg cursor-pointer hover:border-[#165DFF] transition-colors duration-200 flex flex-col items-center gap-2"
                >
                  <Upload className="w-6 h-6 text-[#94a3b8]" />
                  <span className="text-[#64748b] text-sm">点击选择 .py 文件</span>
                </label>
                {selectedFile && (
                  <p className="mt-2 text-green-600 text-sm">{selectedFile.name}</p>
                )}
              </div>

              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">脚本名称</label>
                <input
                  type="text"
                  value={scriptName}
                  onChange={(e) => setScriptName(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  placeholder="输入脚本名称"
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">脚本描述</label>
                <textarea
                  value={scriptDescription}
                  onChange={(e) => setScriptDescription(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200 resize-none"
                  rows={3}
                  placeholder="输入脚本描述"
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">平台</label>
                <select
                  value={platform}
                  onChange={(e) => setPlatform(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2 px-3 text-[#0f172a] text-sm focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                >
                  <option value="android">Android</option>
                  <option value="ios">iOS</option>
                  <option value="harmonyos">HarmonyOS</option>
                </select>
              </div>

              <div className="flex gap-2.5 pt-3">
                <button
                  onClick={() => {
                    setIsModalOpen(false);
                    setSelectedFile(null);
                  }}
                  className="flex-1 px-3 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-sm font-medium rounded-lg transition-colors duration-200"
                >
                  取消
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile}
                  className="flex-1 px-3 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors duration-200"
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
          <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 w-full max-w-5xl mx-4 max-h-[90vh] flex flex-col shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-[#0f172a]">编辑脚本</h2>
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingScript(null);
                  setEditingContent('');
                }}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-colors duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <div className="flex-1 overflow-hidden">
              <textarea
                value={editingContent}
                onChange={(e) => setEditingContent(e.target.value)}
                className="w-full h-full min-h-[50vh] p-3 bg-[#f8fafc] border border-[#e2e8f0] text-[#0f172a] font-mono text-sm resize-none focus:outline-none focus:ring-1 focus:ring-[#165DFF] focus:border-[#165DFF] rounded-lg leading-relaxed transition-all duration-200"
                placeholder="输入脚本内容..."
                spellCheck={false}
              />
            </div>

            <div className="flex gap-2.5 mt-4">
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingScript(null);
                  setEditingContent('');
                }}
                className="flex-1 px-3 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-sm font-medium rounded-lg transition-colors duration-200"
              >
                取消
              </button>
              <button
                onClick={handleSaveEdit}
                className="flex-1 px-3 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white text-sm font-medium rounded-lg transition-colors duration-200"
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
          <div className="bg-white border border-[#e2e8f0] rounded-lg p-5 w-full max-w-md mx-4 shadow-lg">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-[#0f172a]">执行脚本: {selectedScriptForExec.name}</h2>
              <button
                onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-colors duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-[#64748b] text-xs mb-1.5">选择设备 *</label>
                <div className="space-y-1.5">
                  {devices.filter(d => d.status === 'connected').map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="device-select"
                        checked={selectedDeviceId === device.device_id}
                        onChange={() => setSelectedDeviceId(device.device_id)}
                        className="w-3.5 h-3.5 border-[#e2e8f0] bg-[#f8fafc] text-[#165DFF] focus:ring-[#165DFF]"
                      />
                      <span className="text-[#0f172a] text-sm">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-100 text-green-600 text-xs rounded-full">WiFi</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-100 text-blue-600 text-xs rounded-full">USB</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#94a3b8] text-sm">暂无在线设备，请先连接设备</p>
                  )}
                </div>
              </div>

              <div className="flex gap-2.5 pt-3">
                <button
                  onClick={() => { setIsDeviceSelectOpen(false); setSelectedScriptForExec(null); }}
                  className="flex-1 px-3 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] text-sm font-medium rounded-lg transition-colors duration-200"
                >
                  取消
                </button>
                <button
                  onClick={handleExecuteWithDevice}
                  disabled={!selectedDeviceId}
                  className="flex-1 px-3 py-2 bg-[#22c55e] hover:bg-[#16a34a] disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors duration-200"
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