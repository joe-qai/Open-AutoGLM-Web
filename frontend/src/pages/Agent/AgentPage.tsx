import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Bot,
  Play,
  Save,
  RotateCcw,
  Copy,
  Download,
  Bug,
  Edit3,
  Smartphone,
  Terminal,
  Package,
  Sparkles,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useDeviceStore } from '../../stores/deviceStore';
import { useAgentStore } from '../../stores/agentStore';
import { useProjectStore } from '../../stores/projectStore';
import { useApkStore } from '../../stores/apkStore';
import { useModelConfigStore } from '../../stores/modelConfigStore';
import { scriptApi, taskApi } from '../../services/api';
import { Prism as SyntaxHighlighterComponent } from 'react-syntax-highlighter';
import {
  oneDark as atomOneDark,
} from 'react-syntax-highlighter/dist/esm/styles/prism';

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

const platforms = [
  { id: 'android', name: 'Android', color: '#22c55e' },
  { id: 'ios', name: 'iOS', color: '#e5e7eb' },
  { id: 'harmonyos', name: 'HarmonyOS', color: '#3b82f6' },
];

export function AgentPage() {
  const [searchParams] = useSearchParams();
  const { devices, fetchDevices } = useDeviceStore();
  const { projects, fetchProjects } = useProjectStore();
  const { apks, fetchApks } = useApkStore();
  const { configs: modelConfigs, fetchConfigs: fetchModelConfigs } = useModelConfigStore();
  const {
    isExecuting,
    logs,
    executeDirect,
    addLog,
    clearLogs,
  } = useAgentStore();

  const [taskDescription, setTaskDescription] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>(['android']);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedProject, setSelectedProject] = useState('');
  const [scriptContent, setScriptContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [activeTab, setActiveTab] = useState('android');
  const [isSaved, setIsSaved] = useState(true);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [executionPhase, setExecutionPhase] = useState<'idle' | 'executing' | 'completed' | 'failed'>('idle');
  const [showScriptResult, setShowScriptResult] = useState(false);
  const [generatedScriptId, setGeneratedScriptId] = useState<string | null>(null);

  useEffect(() => {
    fetchDevices();
    fetchProjects();
    fetchApks();
    fetchModelConfigs();
    const scriptId = searchParams.get('script_id');
    if (scriptId) {
      scriptApi.getScript(scriptId).then((res: any) => {
        const script = res.script || res;
        setScriptContent(script.content);
        setIsSaved(true);
        setGeneratedScriptId(scriptId);
      });
    }
  }, []);

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
      setCurrentTaskId(taskId);
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
        
        // Display new logs
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
          // Don't add generic message if we have detailed logs
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

      setIsSaved(true);
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

  const openUiDebugger = () => {
    window.open('https://uiauto.dev', '_blank', 'width=1200,height=800');
    addLog('[系统] 已打开UI调试工具');
  };

  const handleScriptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setScriptContent(e.target.value);
    setIsSaved(false);
  };

  const togglePlatform = (platformId: string) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platformId)
        ? prev.filter((p) => p !== platformId)
        : [...prev, platformId]
    );
  };

  return (
    <div className="h-[calc(100vh-112px)] flex flex-col animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bot className="w-6 h-6 text-indigo-400" />
            智能体
          </h1>
          <p className="text-[#94a3b8] mt-1">
            智能体在真机上执行任务，完成后自动生成脚本
          </p>
        </div>

        <div className="flex items-center gap-3">
          {executionPhase === 'idle' && (
            <div className="flex items-center gap-2 text-[#64748b]">
              <div className="w-2 h-2 bg-gray-500 rounded-full" />
              <span className="text-sm">准备就绪</span>
            </div>
          )}
          {executionPhase === 'executing' && (
            <div className="flex items-center gap-2 text-blue-400">
              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
              <span className="text-sm">智能体执行中...</span>
            </div>
          )}
          {executionPhase === 'completed' && (
            <div className="flex items-center gap-2 text-green-400">
              <CheckCircle2 className="w-4 h-4" />
              <span className="text-sm">执行完成，脚本已生成</span>
            </div>
          )}
          {executionPhase === 'failed' && (
            <div className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">执行失败</span>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
        <div className="col-span-4 bg-[#1e293b] border border-[#334155] rounded-xl p-5 flex flex-col">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Terminal className="w-4 h-4" />
            任务配置
          </h3>

          <div className="space-y-4 flex-1 overflow-y-auto">
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">项目</label>
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full px-3 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="">选择项目</option>
                {projects.map((project) => (
                  <option key={project.project_id} value={project.project_id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">目标平台</label>
              <div className="flex gap-2">
                {platforms.map((platform) => (
                  <button
                    key={platform.id}
                    onClick={() => togglePlatform(platform.id)}
                    className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all ${
                      selectedPlatforms.includes(platform.id)
                        ? 'border-indigo-500 bg-indigo-500/20 text-white'
                        : 'border-[#334155] text-[#94a3b8] hover:border-[#475569]'
                    }`}
                  >
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-2"
                      style={{ backgroundColor: platform.color }}
                    />
                    {platform.name}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">选择设备</label>
              <select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                className="w-full px-3 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="">自动选择</option>
                {devices.map((device) => (
                  <option key={device.device_id} value={device.device_id}>
                    {device.name} ({device.platform})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">选择模型</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full px-3 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                {modelConfigs.map((config) => (
                  <option key={config.config_id} value={config.config_id}>
                    {config.name} ({config.provider})
                  </option>
                ))}
                {modelConfigs.length === 0 && (
                  <option value="">暂无可用配置，请先在设置中添加</option>
                )}
              </select>
            </div>

            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">任务描述</label>
              <textarea
                value={taskDescription}
                onChange={(e) => setTaskDescription(e.target.value)}
                placeholder="例如：打开微信，查看最近消息"
                className="w-full h-32 px-3 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white text-sm resize-none focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <button
            onClick={handleExecute}
            disabled={isExecuting || !taskDescription.trim() || executionPhase === 'executing'}
            className={`w-full mt-4 py-3 rounded-lg flex items-center justify-center gap-2 transition-all font-medium ${
              executionPhase === 'executing'
                ? 'bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white'
                : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white'
            }`}
          >
            {executionPhase === 'executing' ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                智能体执行中...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                启动智能体
              </>
            )}
          </button>
        </div>

        <div className="col-span-8 flex flex-col gap-4 min-h-0">
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4 h-64 flex gap-4">
            <div className="w-1/2 bg-[#0f172a] rounded-lg flex items-center justify-center">
              <div className="text-center">
                <Smartphone className="w-12 h-12 text-[#475569] mx-auto mb-2" />
                <p className="text-[#64748b] text-sm">设备截图预览</p>
                <p className="text-[#475569] text-xs mt-1">连接设备后显示</p>
              </div>
            </div>

            <div className="w-1/2 flex flex-col">
              <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                执行日志
              </h4>
              <div className="flex-1 bg-[#0f172a] rounded-lg p-3 overflow-y-auto font-mono text-xs">
                {logs.length === 0 ? (
                  <p className="text-[#64748b]">
                    输入任务描述后点击"启动智能体"
                  </p>
                ) : (
                  logs.map((log, index) => (
                    <div key={index} className="text-[#94a3b8] mb-1">
                      <span className="text-[#64748b]">[{new Date().toLocaleTimeString()}]</span>{' '}
                      {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {showScriptResult && (
            <div className="flex-1 bg-[#1e293b] border border-[#334155] rounded-xl flex flex-col min-h-0">
              <div className="flex items-center justify-between px-4 py-3 border-b border-[#334155]">
                <div className="flex items-center gap-4">
                  <h3 className="text-white font-medium flex items-center gap-2">
                    <Bug className="w-4 h-4 text-amber-400" />
                    生成的脚本
                  </h3>
                  <div className="flex gap-1">
                    {selectedPlatforms.map((platform) => {
                      const platformInfo = platforms.find((p) => p.id === platform);
                      const isActive = activeTab === platform;
                      return (
                        <button
                          key={platform}
                          onClick={() => setActiveTab(platform)}
                          className={`px-3 py-1 rounded text-sm font-medium transition-all ${
                            isActive
                              ? 'text-white shadow-lg'
                              : 'text-[#94a3b8] hover:text-white hover:bg-[#334155]'
                          }`}
                          style={
                            isActive && platformInfo
                              ? {
                                  backgroundColor: platformInfo.color,
                                  boxShadow: `0 0 12px ${platformInfo.color}40`,
                                  color: platform === 'ios' ? '#1e293b' : 'white',
                                }
                              : {}
                          }
                        >
                          {platformInfo?.name}
                        </button>
                      );
                    })}
                  </div>
                  {!isSaved && (
                    <span className="text-orange-400 text-xs flex items-center gap-1">
                      <div className="w-2 h-2 bg-orange-400 rounded-full" />
                      未保存
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={openUiDebugger}
                    className="px-3 py-1.5 text-sm text-[#94a3b8] hover:text-white bg-[#334155] hover:bg-[#475569] rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Bug className="w-4 h-4" />
                    UI调试
                  </button>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="px-3 py-1.5 text-sm text-[#94a3b8] hover:text-white bg-[#334155] hover:bg-[#475569] rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Edit3 className="w-4 h-4" />
                    {isEditing ? '完成' : '编辑'}
                  </button>
                  <button
                    onClick={handleCopy}
                    className="px-3 py-1.5 text-sm text-[#94a3b8] hover:text-white bg-[#334155] hover:bg-[#475569] rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Copy className="w-4 h-4" />
                    复制
                  </button>
                  <button
                    onClick={handleSaveScript}
                    disabled={isSaved}
                    className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Save className="w-4 h-4" />
                    保存
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-3 py-1.5 text-sm text-[#94a3b8] hover:text-white bg-[#334155] hover:bg-[#475569] rounded-lg flex items-center gap-1.5 transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    下载
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-hidden">
                {isEditing ? (
                  <textarea
                    value={scriptContent}
                    onChange={handleScriptChange}
                    className="w-full h-full bg-[#0f172a] text-[#e2e8f0] p-4 font-mono text-sm resize-none focus:outline-none"
                    placeholder="脚本内容..."
                  />
                ) : (
                  <SyntaxHighlighterComponent
                    language={getLanguage(activeTab)}
                    style={customDarkStyle}
                    customStyle={{ height: '100%', margin: 0 }}
                  >
                    {scriptContent || '# No script generated yet'}
                  </SyntaxHighlighterComponent>
                )}
              </div>
            </div>
          )}

          {!showScriptResult && (
            <div className="flex-1 bg-[#1e293b] border border-[#334155] rounded-xl flex items-center justify-center">
              <div className="text-center">
                <Sparkles className="w-16 h-16 text-[#475569] mx-auto mb-4" />
                <h3 className="text-white text-lg font-medium mb-2">智能体将在这里执行任务</h3>
                <p className="text-[#64748b] text-sm max-w-md">
                  输入任务描述后，智能体将在真机上自动执行操作，
                  完成后自动生成可复用的脚本
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
