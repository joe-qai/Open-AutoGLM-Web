import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Bot,
  Play,
  Save,
  Copy,
  Download,
  Smartphone,
  Terminal,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  Wifi,
  Usb,
} from 'lucide-react';
import { useDeviceStore } from '../../stores/deviceStore';
import { useAgentStore } from '../../stores/agentStore';
import { useModelConfigStore } from '../../stores/modelConfigStore';
import { scriptApi, taskApi } from '../../services/api';
import controlApi from '../../services/controlApi';
import { Prism as SyntaxHighlighterComponent } from 'react-syntax-highlighter';
import {
  oneDark as atomOneDark,
} from 'react-syntax-highlighter/dist/esm/styles/prism';
import ScrcpyPlayer from '../../components/ScrcpyPlayer/ScrcpyPlayer';

const getLanguage = (platform: string): string => {
  switch (platform) {
    case 'ios':
      return 'swift';
    case 'harmonyos':
      return 'java';
    case 'android':
    default:
      return 'python';
  }
};

const customDarkStyle = {
  ...atomOneDark,
  'pre[class*="language-"]': {
    ...atomOneDark['pre[class*="language-"]'],
    backgroundColor: '#0f172a',
    borderRadius: '0',
    margin: '0',
    padding: '16px',
    fontSize: '14px',
    minHeight: '100%',
  },
  'code[class*="language-"]': {
    ...atomOneDark['code[class*="language-"]'],
    fontFamily: "'Fira Code', 'Monaco', 'Consolas', monospace",
    backgroundColor: 'transparent',
  },
  '::-webkit-scrollbar': {
    width: '8px',
    height: '8px',
  },
  '::-webkit-scrollbar-track': {
    backgroundColor: '#0f172a',
  },
  '::-webkit-scrollbar-thumb': {
    backgroundColor: '#334155',
    borderRadius: '4px',
  },
  '::-webkit-scrollbar-thumb:hover': {
    backgroundColor: '#475569',
  },
};

export function AgentPage() {
  const [searchParams] = useSearchParams();
  const { devices, fetchDevices } = useDeviceStore();
  const { configs: modelConfigs, fetchConfigs: fetchModelConfigs } = useModelConfigStore();
  const {
    logs,
    executeDirect,
    addLog,
    clearLogs,
  } = useAgentStore();

  const [taskDescription, setTaskDescription] = useState('');
  const [selectedPlatforms] = useState<string[]>(['android']);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [scriptContent, setScriptContent] = useState('');
  const [executionPhase, setExecutionPhase] = useState<'idle' | 'executing' | 'completed' | 'failed'>('idle');
  const [showScriptResult, setShowScriptResult] = useState(false);
  const [generatedScriptId, setGeneratedScriptId] = useState<string | null>(null);
  const [activeTab] = useState('android');

  useEffect(() => {
    fetchDevices();
    fetchModelConfigs();
    const scriptId = searchParams.get('script_id');
    if (scriptId) {
      scriptApi.getScript(scriptId).then((res: any) => {
        const script = res.script || res;
        setScriptContent(script.content);
        setGeneratedScriptId(scriptId);
      });
    }
  }, []);

  useEffect(() => {
    if (devices.length > 0 && !selectedDevice) {
      const usbDevices = devices.filter(d => d.status === 'connected' && d.connection_type === 'usb');
      const connectedDevices = devices.filter(d => d.status === 'connected');
      
      const deviceToSelect = usbDevices.length > 0 ? usbDevices[0] : connectedDevices[0];
      
      if (deviceToSelect) {
        setSelectedDevice(deviceToSelect.device_id);
        addLog(`[系统] 自动连接设备: ${deviceToSelect.name}`);
      }
    }
  }, [devices, selectedDevice, addLog]);

  useEffect(() => {
    if (modelConfigs.length > 0 && !selectedModel) {
      const defaultCfg = modelConfigs.find(c => c.is_default);
      if (defaultCfg) {
        setSelectedModel(defaultCfg.config_id);
      } else {
        setSelectedModel(modelConfigs[0].config_id);
      }
    }
  }, [modelConfigs]);

  const handleExecute = async () => {
    if (!taskDescription.trim()) return;

    clearLogs();
    setExecutionPhase('executing');
    setShowScriptResult(false);
    setScriptContent('');
    setGeneratedScriptId(null);

    addLog('[系统] 智能体开始执行任务...');
    addLog(`[系统] 任务描述: ${taskDescription}`);
    addLog(`[系统] 目标平台: ${selectedPlatforms.join(', ')}`);
    if (selectedDevice) {
      addLog(`[系统] 目标设备: ${selectedDevice}`);
    }

    const taskId = await executeDirect({
      task_description: taskDescription,
      device_id: selectedDevice || undefined,
      platform: selectedPlatforms[0],
      max_steps: 100,
      mode: 'llm',
    });

    if (taskId) {
      addLog(`[系统] 任务已启动，任务ID: ${taskId}`);
      addLog('[系统] 智能体正在设备上执行操作...');

      pollTaskStatus(taskId);
    } else {
      addLog('[错误] 任务启动失败');
      setExecutionPhase('failed');
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    const pollInterval = 2000;
    const maxPolls = 900;
    let pollCount = 0;
    let lastLogCount = 0;

    const poll = async () => {
      try {
        const [task, logsResponse] = await Promise.all([
          taskApi.getTask(taskId),
          taskApi.getTaskLogs(taskId, 50),
        ]);
        
        const taskData = (task as any).task || task;
        
        const logs = (logsResponse as any).logs || [];
        const newLogs = logs.slice(lastLogCount);
        newLogs.forEach((log: any) => {
          const timestamp = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
          const level = log.level || 'INFO';
          const message = log.message || '';
          
          if (level === 'ERROR') {
            addLog(`[${timestamp}] [错误] ${message}`);
          } else {
            addLog(`[${timestamp}] ${message}`);
          }
        });
        lastLogCount = logs.length;

        if (taskData.status === 'completed') {
          addLog('[系统] 任务执行完成！');
          addLog('[系统] 正在生成脚本...');
          generateScriptFromTask(taskId);
          return;
        } else if (taskData.status === 'failed') {
          addLog('[错误] 任务执行失败');
          if (taskData.error_message) {
            addLog(`[错误] ${taskData.error_message}`);
          }
          setExecutionPhase('failed');
          return;
        } else if (taskData.status === 'executing' || taskData.status === 'running') {
          if (newLogs.length === 0) {
            addLog('[系统] 智能体正在执行中...');
          }
        }

        pollCount++;
        if (pollCount < maxPolls) {
          setTimeout(poll, pollInterval);
        } else {
          addLog('[错误] 任务执行超时');
          setExecutionPhase('failed');
        }
      } catch (error) {
        addLog(`[错误] 获取任务状态失败: ${error}`);
        setExecutionPhase('failed');
      }
    };

    setTimeout(poll, pollInterval);
  };

  const generateScriptFromTask = async (taskId: string) => {
    try {
      addLog('[系统] 基于执行历史生成脚本...');

      const task = await taskApi.getTask(taskId) as any;
      const taskData = task.task || task;

      const history = taskData.history || [];
      if (history.length === 0) {
        addLog('[系统] 无执行历史，生成空脚本');
      }

      const scriptLines = [
        `# Auto-generated script for: ${taskDescription}`,
        `# Platform: ${selectedPlatforms[0]}`,
        `# Generated at: ${new Date().toISOString()}`,
        '',
        'import time',
        'import sys',
        "sys.path.append('/path/to/project')",
        '',
        'from phone_agent import DeviceFactory, set_device_type, DeviceType',
        'from phone_agent.config.apps import get_package_name',
        '',
        '# Initialize device',
        `set_device_type(DeviceType.${selectedPlatforms[0].toUpperCase()})`,
        '',
        'def main():',
      ];

      history.forEach((step: any, index: number) => {
        const action = step.action || '';
        const params = step.parameters || {};
        const reasoning = step.reasoning || '';

        if (action === 'launch_app') {
          const appName = params.app_name || '';
          scriptLines.push(`    # Step ${index + 1}: 启动应用`);
          scriptLines.push(`    DeviceFactory.launch_app("${appName}")`);
          scriptLines.push(`    time.sleep(2)`);
        } else if (action === 'tap_element') {
          if (params.element_index !== undefined) {
            scriptLines.push(`    # Step ${index + 1}: 点击元素 ${params.element_index}`);
            scriptLines.push(`    # ${reasoning}`);
            scriptLines.push(`    # TODO: 实现点击逻辑`);
          } else if (params.x !== undefined && params.y !== undefined) {
            scriptLines.push(`    # Step ${index + 1}: 点击坐标 (${params.x}, ${params.y})`);
            scriptLines.push(`    # ${reasoning}`);
            scriptLines.push(`    DeviceFactory.tap(${params.x}, ${params.y})`);
          }
        } else if (action === 'type_text') {
          const text = params.text || '';
          scriptLines.push(`    # Step ${index + 1}: 输入文本`);
          scriptLines.push(`    # ${reasoning}`);
          scriptLines.push(`    DeviceFactory.type_text("${text}")`);
        } else if (action === 'swipe') {
          const direction = params.direction || 'up';
          scriptLines.push(`    # Step ${index + 1}: 滑动${direction}`);
          scriptLines.push(`    # ${reasoning}`);
          scriptLines.push(`    DeviceFactory.swipe(direction="${direction}")`);
        } else if (action === 'back') {
          scriptLines.push(`    # Step ${index + 1}: 返回`);
          scriptLines.push(`    DeviceFactory.back()`);
        } else if (action === 'home') {
          scriptLines.push(`    # Step ${index + 1}: 返回主页`);
          scriptLines.push(`    DeviceFactory.home()`);
        } else if (action === 'wait') {
          const duration = params.duration || 1000;
          scriptLines.push(`    # Step ${index + 1}: 等待`);
          scriptLines.push(`    time.sleep(${duration / 1000})`);
        } else if (action === 'finish') {
          scriptLines.push(`    # 任务完成`);
          scriptLines.push(`    print("Task completed: ${params.message || ''}")`);
        }
      });

      scriptLines.push('');
      scriptLines.push('if __name__ == "__main__":');
      scriptLines.push('    main()');

      const generatedScript = scriptLines.join('\n');
      setScriptContent(generatedScript);
      setShowScriptResult(true);
      setExecutionPhase('completed');
      addLog('[系统] 脚本生成完成，请确认是否保存');
    } catch (error) {
      addLog(`[错误] 脚本生成失败: ${error}`);
      setExecutionPhase('failed');
    }
  };

  const handleSaveScript = async () => {
    if (!scriptContent.trim()) return;

    addLog('[系统] 正在保存脚本...');

    try {
      let scriptId = generatedScriptId;

      if (scriptId) {
        await scriptApi.updateScript(scriptId, { content: scriptContent });
        addLog('[系统] 脚本更新成功');
      } else {
        const response = await scriptApi.createScript({
          name: taskDescription.substring(0, 50) + '...',
          description: taskDescription,
          platform: selectedPlatforms[0],
          content: scriptContent,
        }) as unknown as { script_id: string };
        scriptId = response.script_id;
        setGeneratedScriptId(scriptId);
        addLog('[系统] 脚本保存成功');
      }
    } catch (error) {
      addLog('[错误] 脚本保存失败');
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(scriptContent);
    addLog('[系统] 脚本已复制到剪贴板');
  };

  const handleDownload = () => {
    const blob = new Blob([scriptContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `script_${activeTab}.py`;
    a.click();
    URL.revokeObjectURL(url);
    addLog('[系统] 脚本已下载');
  };

  const getConnectedDevices = () => {
    return devices.filter(d => d.status === 'connected');
  };

  const getSelectedDeviceInfo = () => {
    return devices.find(d => d.device_id === selectedDevice);
  };

  return (
    <div className="h-[calc(100vh-112px)] flex gap-6 p-6">
      {/* 左侧：设备列表 */}
      <div className="w-72 bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 flex flex-col rounded-2xl shadow-xl">
        <div className="p-5 border-b border-slate-700/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Smartphone className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-lg">设备列表</h2>
              <p className="text-slate-400 text-xs mt-0.5">已连接 {getConnectedDevices().length} 台设备</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-2">
            {getConnectedDevices().length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-slate-700/50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Smartphone className="w-8 h-8 text-slate-500" />
                </div>
                <p className="text-slate-400 text-sm">暂无连接的设备</p>
                <p className="text-slate-500 text-xs mt-1">请连接设备后重试</p>
              </div>
            ) : (
              getConnectedDevices().map((device) => {
                const isSelected = selectedDevice === device.device_id;
                const connectionType = device.connection_type === 'usb' ? <Usb className="w-3 h-3" /> : <Wifi className="w-3 h-3" />;
                
                return (
                  <button
                    key={device.device_id}
                    onClick={() => setSelectedDevice(device.device_id)}
                    className={`w-full flex items-center gap-3 p-3.5 rounded-xl transition-all duration-300 ${
                      isSelected
                        ? 'bg-gradient-to-r from-indigo-500/20 to-purple-500/20 border border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                        : 'bg-slate-700/30 hover:bg-slate-700/50 border border-transparent hover:border-slate-600/50'
                    }`}
                  >
                    <div className={`w-2.5 h-2.5 rounded-full ${
                      device.status === 'connected' ? 'bg-emerald-400 animate-pulse shadow-lg shadow-emerald-400/50' :
                      device.status === 'busy' ? 'bg-amber-400 animate-pulse shadow-lg shadow-amber-400/50' :
                      device.status === 'error' ? 'bg-red-400 animate-pulse shadow-lg shadow-red-400/50' :
                      'bg-slate-500'
                    }`} />
                    <div className="flex-1 text-left">
                      <p className="text-white text-sm font-medium truncate">{device.name}</p>
                      <p className="text-slate-400 text-xs flex items-center gap-1">
                        {connectionType}
                        {device.device_id}
                      </p>
                    </div>
                    <ChevronRight className={`w-4 h-4 transition-all duration-300 ${isSelected ? 'rotate-90 text-indigo-400' : 'text-slate-500'}`} />
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* 模型选择 */}
        <div className="p-4 border-t border-slate-700/30">
          <label className="text-slate-400 text-xs mb-2 block">选择模型</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          >
            {modelConfigs.map((config) => (
              <option key={config.config_id} value={config.config_id}>
                {config.name} {config.is_default && '(默认)'}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 中间：指令输入区 */}
      <div className="flex-1 flex flex-col bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-xl">
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/30">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Terminal className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">指令输入</h3>
              <p className="text-slate-400 text-xs">
                {selectedDevice ? `目标设备: ${getSelectedDeviceInfo()?.name}` : '请选择设备'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {executionPhase === 'idle' && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 rounded-full">
                <div className="w-2 h-2 bg-slate-400 rounded-full" />
                <span className="text-slate-300 text-xs">准备就绪</span>
              </div>
            )}
            {executionPhase === 'executing' && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/20 rounded-full">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                <span className="text-blue-300 text-xs">智能体执行中...</span>
              </div>
            )}
            {executionPhase === 'completed' && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 rounded-full">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-300 text-xs">执行完成</span>
              </div>
            )}
            {executionPhase === 'failed' && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 rounded-full">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <span className="text-red-300 text-xs">执行失败</span>
              </div>
            )}
          </div>
        </div>

        {/* 聊天内容区域 */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {logs.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-20 h-20 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-3xl flex items-center justify-center mx-auto mb-6">
                  <Sparkles className="w-10 h-10 text-indigo-400" />
                </div>
                <h3 className="text-white text-lg font-medium mb-2">智能体就绪</h3>
                <p className="text-slate-400 text-sm">输入指令，智能体将在设备上执行</p>
                <div className="mt-6 flex items-center justify-center gap-4">
                  <span className="px-3 py-1 bg-slate-700/50 rounded-full text-slate-400 text-xs">自动连接</span>
                  <span className="px-3 py-1 bg-slate-700/50 rounded-full text-slate-400 text-xs">实时预览</span>
                  <span className="px-3 py-1 bg-slate-700/50 rounded-full text-slate-400 text-xs">脚本生成</span>
                </div>
              </div>
            ) : (
              logs.map((log, index) => {
                const isError = log.includes('[错误]');
                const isSystem = log.includes('[系统]');
                
                return (
                  <div key={index} className={`flex gap-3 ${isSystem ? 'justify-end' : 'justify-start'}`}>
                    {isSystem ? (
                      <div className="max-w-[80%]">
                        <div className="bg-slate-700/50 backdrop-blur-sm rounded-2xl rounded-br-md px-4 py-3 border border-slate-600/30">
                          <p className="text-slate-300 text-sm whitespace-pre-wrap">{log}</p>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="w-9 h-9 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-indigo-500/20">
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                        <div className="max-w-[80%]">
                          <div className={`rounded-2xl rounded-bl-md px-4 py-3 border ${isError ? 'bg-red-500/10 border-red-500/30' : 'bg-slate-700/50 border-slate-600/30'}`}>
                            <p className={`text-sm whitespace-pre-wrap ${isError ? 'text-red-300' : 'text-slate-300'}`}>
                              {log}
                            </p>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 底部输入区域 */}
        <div className="p-5 border-t border-slate-700/30 bg-slate-800/50">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3">
              <div className="flex-1 bg-slate-700/50 border border-slate-600/50 rounded-2xl p-4 shadow-lg shadow-black/10">
                <textarea
                  value={taskDescription}
                  onChange={(e) => setTaskDescription(e.target.value)}
                  placeholder="您想做什么？（Enter 发送，Shift+Enter 换行）"
                  className="w-full bg-transparent text-white text-sm resize-none focus:outline-none placeholder-slate-400"
                  rows={2}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleExecute();
                    }
                  }}
                />
              </div>
              <button
                onClick={handleExecute}
                disabled={!taskDescription.trim() || executionPhase === 'executing'}
                className={`px-6 py-4 rounded-2xl font-medium flex items-center gap-2 transition-all duration-300 shadow-lg ${
                  executionPhase === 'executing'
                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-400 hover:to-cyan-400 disabled:opacity-50 text-white shadow-blue-500/30'
                    : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white shadow-indigo-500/30'
                }`}
              >
                {executionPhase === 'executing' ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Play className="w-5 h-5" />
                )}
                {executionPhase === 'executing' ? '执行中' : '发送'}
              </button>
            </div>
            <p className="text-slate-500 text-xs mt-3 text-right">按 Enter 发送，Shift+Enter 换行</p>
          </div>
        </div>
      </div>

      {/* 右侧：设备实时预览 */}
      <div className="w-96 flex flex-col bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl shadow-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/30">
          <div className="flex items-center gap-3">
            {selectedDevice ? (
              <>
                <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-emerald-600 rounded-lg flex items-center justify-center shadow-lg shadow-green-500/20">
                  <Smartphone className="w-4 h-4 text-white" />
                </div>
                <div>
                  <span className="text-white text-sm font-medium">
                    {getSelectedDeviceInfo()?.name}
                  </span>
                  <p className="text-slate-400 text-xs">实时预览</p>
                </div>
              </>
            ) : (
              <span className="text-slate-400 text-sm">请选择设备</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-emerald-400 text-xs font-medium">在线</span>
          </div>
        </div>

        <div className="flex-1 p-4">
          {selectedDevice ? (
            <div className="relative bg-slate-900 rounded-[2rem] shadow-2xl shadow-black/30 aspect-[9/16] overflow-hidden border-4 border-slate-700">
              <ScrcpyPlayer
                deviceId={selectedDevice}
                enableControl={true}
                onTapSuccess={() => console.log('Tap success')}
                onTapError={(error) => console.error('Tap error:', error)}
                onSwipeSuccess={() => console.log('Swipe success')}
                onSwipeError={(error) => console.error('Swipe error:', error)}
              />
              {/* 设备顶部装饰 */}
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-6 bg-slate-900 rounded-b-2xl z-20" />
              {/* 设备底部装饰 */}
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 w-20 h-1.5 bg-slate-700 rounded-full z-20" />
            </div>
          ) : (
            <div className="h-full bg-slate-700/30 rounded-2xl flex items-center justify-center border border-slate-600/30">
              <div className="text-center">
                <div className="w-16 h-16 bg-slate-600/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Smartphone className="w-8 h-8 text-slate-500" />
                </div>
                <p className="text-slate-400 text-sm">选择设备以查看预览</p>
                <p className="text-slate-500 text-xs mt-1">自动连接 USB 设备</p>
              </div>
            </div>
          )}
        </div>

        {/* 操作提示 */}
        <div className="px-5 py-3 border-t border-slate-700/30">
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-slate-700/50 rounded-md flex items-center justify-center">
                <span className="text-white text-[10px] font-medium">T</span>
              </div>
              <span>点击</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-slate-700/50 rounded-md flex items-center justify-center">
                <span className="text-white text-[10px] font-medium">S</span>
              </div>
              <span>滑动</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-5 h-5 bg-slate-700/50 rounded-md flex items-center justify-center">
                <span className="text-white text-[10px] font-medium">W</span>
              </div>
              <span>缩放</span>
            </div>
          </div>
        </div>

        {/* 脚本结果区域 */}
        {showScriptResult && (
          <div className="border-t border-slate-700/30 p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-white text-sm font-medium flex items-center gap-2">
                <Terminal className="w-4 h-4 text-amber-400" />
                生成的脚本
              </h4>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleCopy}
                  className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg transition-all duration-200"
                  title="复制"
                >
                  <Copy className="w-4 h-4 text-slate-300" />
                </button>
                <button
                  onClick={handleSaveScript}
                  className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg transition-all duration-200"
                  title="保存"
                >
                  <Save className="w-4 h-4 text-slate-300" />
                </button>
                <button
                  onClick={handleDownload}
                  className="p-2 bg-slate-700/50 hover:bg-slate-600/50 rounded-lg transition-all duration-200"
                  title="下载"
                >
                  <Download className="w-4 h-4 text-slate-300" />
                </button>
              </div>
            </div>
            <div className="bg-slate-900/80 rounded-xl overflow-hidden max-h-48 overflow-y-auto border border-slate-700/50">
              <SyntaxHighlighterComponent
                language={getLanguage(activeTab)}
                style={customDarkStyle}
                customStyle={{ height: '100%', margin: 0, maxHeight: '192px' }}
              >
                {scriptContent || '# No script generated yet'}
              </SyntaxHighlighterComponent>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}