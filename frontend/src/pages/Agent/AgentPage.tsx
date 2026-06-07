import { useState, useEffect, useRef } from 'react';
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
import { scriptApi } from '../../services/api';
import { Prism as SyntaxHighlighterComponent } from 'react-syntax-highlighter';
import {
  oneDark as atomOneDark,
} from 'react-syntax-highlighter/dist/esm/styles/prism';
import ScrcpyPlayer from '../../components/ScrcpyPlayer/ScrcpyPlayer';

// WebSocket 配置
const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8005').replace('http', 'ws');
const RECONNECT_INTERVAL = 3000;

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
    padding: '12px',
    fontSize: '12px',
    minHeight: '100%',
  },
  'code[class*="language-"]': {
    ...atomOneDark['code[class*="language-"]'],
    fontFamily: "'Fira Code', 'Monaco', 'Consolas', monospace",
    backgroundColor: 'transparent',
  },
  '::-webkit-scrollbar': {
    width: '6px',
    height: '6px',
  },
  '::-webkit-scrollbar-track': {
    backgroundColor: '#0f172a',
  },
  '::-webkit-scrollbar-thumb': {
    backgroundColor: '#334155',
    borderRadius: '3px',
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
  const [maxSteps, setMaxSteps] = useState(10);
  const [selectedPlatforms] = useState<string[]>(['android']);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [scriptContent, setScriptContent] = useState('');
  const [executionPhase, setExecutionPhase] = useState<'idle' | 'executing' | 'completed' | 'failed'>('idle');
  const [showScriptResult, setShowScriptResult] = useState(false);
  const [generatedScriptId, setGeneratedScriptId] = useState<string | null>(null);
  const [activeTab] = useState('android');
  const [simulateMode, setSimulateMode] = useState(false); // 模拟模式开关，默认关闭
  
  // 日志滚动 ref
  const logsContainerRef = useRef<HTMLDivElement>(null);
  
  // WebSocket 状态
  const wsRef = useRef<WebSocket | null>(null);
  const currentTaskIdRef = useRef<string | null>(null);
  
  // 模拟执行步骤
  const simulateSteps = [
    { action: '观察屏幕', result: '当前屏幕显示手机主界面，包含多个应用图标' },
    { action: '识别目标应用', result: '成功识别到微信应用图标位于屏幕底部' },
    { action: '执行点击操作', result: '点击微信图标，应用正在启动...' },
    { action: '等待应用加载', result: '微信应用已成功打开' },
    { action: '任务完成', result: '成功启动微信应用' },
  ];

  // 初始化 WebSocket 连接
  useEffect(() => {
    const clientId = `agent_${Date.now()}`;
    const socket = new WebSocket(`${WS_URL}/api/v1/ws/${clientId}`);
    
    socket.onopen = () => {
      console.log('WebSocket connected');
    };
    
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        // 处理 WebSocket 消息
        if (message.type === 'agent_step' && message.task_id === currentTaskIdRef.current) {
          const data = message.data;
          const step = data.step || 0;
          const action = data.action || data.proposed_action || '';
          const result = data.result || '';
          const eventType = data.event || '';
          
          if (eventType === 'completed') {
            addLog(`[系统] 任务执行完成！共执行 ${step} 步`);
            setExecutionPhase('completed');
            currentTaskIdRef.current = null;
          } else if (eventType === 'error' || eventType === 'failed') {
            addLog(`[错误] ${result || '执行失败'}`);
            setExecutionPhase('failed');
            currentTaskIdRef.current = null;
          } else if (action || result) {
            const logMsg = `[Step ${step}] ${action}${result ? ': ' + result : ''}`;
            addLog(logMsg);
          }
        } else if (message.type === 'subscribed') {
          console.log('Subscribed to task:', message.task_id);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    socket.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    wsRef.current = socket;
    
    return () => {
      socket.close();
    };
  }, []);

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

  // 自动滚动日志
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const handleExecute = async () => {
    if (!taskDescription.trim()) {
      addLog('[错误] 任务描述不能为空，请输入要执行的任务');
      return;
    }

    // 模拟模式：跳过设备检查，使用虚拟设备
    if (!simulateMode && !selectedDevice) {
      addLog('[错误] 请先选择一个设备');
      addLog('[提示] 您可以在左侧设备列表中选择已连接的设备');
      return;
    }

    clearLogs();
    setExecutionPhase('executing');
    setShowScriptResult(false);
    setScriptContent('');
    setGeneratedScriptId(null);

    addLog('[系统] 智能体开始执行任务...');
    addLog(`[系统] 任务描述: ${taskDescription}`);
    addLog(`[系统] 目标平台: ${selectedPlatforms.join(', ')}`);
    addLog(`[系统] 最大步骤: ${maxSteps}`);
    
    if (simulateMode) {
      addLog('[系统] 【模拟模式】已启用虚拟设备和VLM模型');
      addLog('[系统] 目标设备: 虚拟设备 (模拟模式)');
      addLog('[系统] VLM模型: 模拟视觉识别引擎 v1.0');
    } else {
      addLog(`[系统] 目标设备: ${selectedDevice}`);
      addLog('[系统] 正在连接后端服务...');
    }

    // 模拟模式：执行模拟步骤
    if (simulateMode) {
      addLog('[系统] 正在通过 VLM 视觉模型驱动 Phone Agent...');
      addLog('[系统] 【模拟模式】开始模拟执行...');
      
      const stepsToExecute = Math.min(maxSteps, simulateSteps.length);
      
      for (let i = 0; i < stepsToExecute; i++) {
        await new Promise(resolve => setTimeout(resolve, 1500)); // 模拟每步延迟
        const step = simulateSteps[i];
        addLog(`[步骤 ${i + 1}/${stepsToExecute}] ${step.action}`);
        addLog(`[结果] ${step.result}`);
        
        if (step.action === '任务完成') {
          break;
        }
      }
      
      addLog('[系统] 任务执行完成！');
      addLog('[系统] 【模拟模式】已成功模拟VLM视觉模型驱动的Phone Agent执行流程');
      setExecutionPhase('completed');
      return;
    }

    // 真实模式：调用后端API
    try {
      // 使用 phone_agent 的 agent 能力
      const taskId = await executeDirect({
        task_description: taskDescription,
        device_id: selectedDevice || undefined,
        platform: selectedPlatforms[0],
        max_steps: maxSteps,
        mode: 'vlm',
        save_task: false,
      });

      if (taskId) {
        addLog(`[系统] 任务已启动，任务ID: ${taskId}`);
        addLog('[系统] 智能体正在设备上执行操作...');
        addLog('[系统] 正在通过 VLM 视觉模型驱动 Phone Agent...');
        
        // 订阅 WebSocket 任务更新
        currentTaskIdRef.current = taskId;
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          addLog('[系统] 已建立实时日志连接');
          wsRef.current.send(JSON.stringify({
            type: 'subscribe',
            task_id: taskId,
          }));
        } else {
          addLog('[警告] WebSocket连接未建立，可能无法接收实时日志');
        }

        // 设置超时检测
        setTimeout(() => {
          if (executionPhase === 'executing' && currentTaskIdRef.current === taskId) {
            addLog('[警告] 任务执行超时，可能需要检查设备连接或模型配置');
            addLog('[提示] 请检查：1.设备是否正常连接 2.VLM模型是否正确配置 3.网络连接是否正常');
          }
        }, maxSteps * 30000); // 每步最多30秒
        
        setExecutionPhase('executing');
      } else {
        addLog('[错误] 任务启动失败');
        addLog('[提示] 可能的原因：');
        addLog('[提示] 1. 后端服务未启动，请运行: cd backend && python run.py');
        addLog('[提示] 2. 模型配置不正确，请在"模型配置"页面检查');
        addLog('[提示] 3. 设备连接异常，请重新连接设备');
        setExecutionPhase('failed');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || String(error);
      addLog(`[错误] 任务启动失败: ${errorMessage}`);
      if (error.response?.status === 404) {
        addLog('[提示] 后端服务未找到，请确认后端服务已启动');
        addLog('[提示] 启动命令: cd backend && python run.py');
      } else if (error.response?.status === 500) {
        addLog('[提示] 后端服务内部错误，请检查服务器日志');
        addLog('[提示] 可能是模型配置问题或设备连接问题');
      } else if (error.code === 'ECONNREFUSED') {
        addLog('[提示] 无法连接到后端服务');
        addLog('[提示] 请确保后端服务正在运行: cd backend && python run.py');
        addLog('[提示] 默认端口: http://localhost:8005');
      } else if (error.code === 'ENETUNREACH') {
        addLog('[提示] 网络不可达，请检查网络连接');
      }
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
    <div className="h-[calc(100vh-100px)] flex gap-4 p-5">
      {/* VLM视觉模型提醒 */}
      <div className="absolute top-16 left-1/2 -translate-x-1/2 px-4 py-2 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-full flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-[#165DFF]" />
        <span className="text-[#165DFF] text-xs font-medium">当前项目基于 VLM 视觉大模型驱动的 Phone Agent</span>
      </div>

      {/* 左侧：设备列表 */}
      <div className="w-64 bg-white border border-[#e2e8f0] flex flex-col rounded-lg">
        <div className="p-4 border-b border-[#e2e8f0]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-[#165DFF] rounded-lg flex items-center justify-center">
              <Smartphone className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-[#0f172a] font-semibold text-sm">设备列表</h2>
              <p className="text-[#64748b] text-xs mt-0.5">已连接 {getConnectedDevices().length} 台设备</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3">
          <div className="space-y-1.5">
            {getConnectedDevices().length === 0 ? (
              <div className="text-center py-8">
                <div className="w-12 h-12 bg-[#f8fafc] rounded-xl flex items-center justify-center mx-auto mb-3">
                  <Smartphone className="w-6 h-6 text-[#94a3b8]" />
                </div>
                <p className="text-[#64748b] text-xs">暂无连接的设备</p>
                <p className="text-[#94a3b8] text-xs mt-1">请连接设备后重试</p>
              </div>
            ) : (
              getConnectedDevices().map((device) => {
                const isSelected = selectedDevice === device.device_id;
                const connectionType = device.connection_type === 'usb' ? <Usb className="w-3 h-3" /> : <Wifi className="w-3 h-3" />;
                
                return (
                  <button
                    key={device.device_id}
                    onClick={() => setSelectedDevice(device.device_id)}
                    className={`w-full flex items-center gap-2.5 p-3 rounded-lg transition-all duration-200 ${
                      isSelected
                        ? 'bg-[#e8f0fe] border border-[#165DFF]'
                        : 'bg-[#f8fafc] hover:bg-[#f1f5f9] border border-transparent'
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full ${
                      device.status === 'connected' ? 'bg-[#22c55e]' :
                      device.status === 'busy' ? 'bg-[#f59e0b]' :
                      device.status === 'error' ? 'bg-[#ef4444]' :
                      'bg-[#94a3b8]'
                    }`} />
                    <div className="flex-1 text-left min-w-0">
                      <p className="text-[#0f172a] text-xs font-medium truncate">{device.name}</p>
                      <p className="text-[#64748b] text-xs flex items-center gap-1">
                        {connectionType}
                        {device.device_id}
                      </p>
                    </div>
                    <ChevronRight className={`w-4 h-4 transition-colors ${isSelected ? 'text-[#165DFF]' : 'text-[#94a3b8]'}`} />
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* 模型选择 */}
        <div className="p-3 border-t border-[#e2e8f0]">
          <label className="text-[#64748b] text-xs mb-1.5 block">选择模型</label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg px-3 py-2 text-[#0f172a] text-xs focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all"
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
      <div className="flex-1 flex flex-col bg-white border border-[#e2e8f0] rounded-lg">
        {/* 顶部标题栏 */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-[#e2e8f0]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[#165DFF] rounded-lg flex items-center justify-center">
              <Terminal className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-[#0f172a] font-semibold text-sm">实时日志</h3>
              <p className="text-[#64748b] text-xs">
                {selectedDevice ? `目标设备: ${getSelectedDeviceInfo()?.name}` : '请选择设备'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {executionPhase === 'idle' && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-[#f8fafc] rounded-full">
                <div className="w-1.5 h-1.5 bg-[#94a3b8] rounded-full" />
                <span className="text-[#64748b] text-xs">准备就绪</span>
              </div>
            )}
            {executionPhase === 'executing' && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 rounded-full">
                <div className="w-1.5 h-1.5 bg-[#165DFF] rounded-full animate-pulse" />
                <span className="text-[#165DFF] text-xs">智能体执行中</span>
              </div>
            )}
            {executionPhase === 'completed' && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 rounded-full">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#22c55e]" />
                <span className="text-[#22c55e] text-xs">执行完成</span>
              </div>
            )}
            {executionPhase === 'failed' && (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-red-50 rounded-full">
                <AlertCircle className="w-3.5 h-3.5 text-[#ef4444]" />
                <span className="text-[#ef4444] text-xs">执行失败</span>
              </div>
            )}
          </div>
        </div>

        {/* 实时日志区域 */}
        <div ref={logsContainerRef} className="flex-1 overflow-y-auto px-6 py-4 bg-[#fafbfc]">
          <div className="max-w-3xl mx-auto space-y-4">
            {logs.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Sparkles className="w-8 h-8 text-[#165DFF]" />
                </div>
                <h3 className="text-[#0f172a] text-base font-medium mb-2">智能体就绪</h3>
                <p className="text-[#64748b] text-xs">输入指令，智能体将在设备上执行</p>
                <div className="mt-4 flex items-center justify-center gap-3">
                  <span className="px-2.5 py-1 bg-blue-50 rounded-full text-[#165DFF] text-xs">自动连接</span>
                  <span className="px-2.5 py-1 bg-blue-50 rounded-full text-[#165DFF] text-xs">实时预览</span>
                  <span className="px-2.5 py-1 bg-blue-50 rounded-full text-[#165DFF] text-xs">脚本生成</span>
                </div>
              </div>
            ) : (
              logs.map((log, index) => {
                const isError = log.includes('[错误]');
                const isSystem = log.includes('[系统]');
                
                return (
                  <div key={index} className={`flex gap-2.5 ${isSystem ? 'justify-end' : 'justify-start'}`}>
                    {isSystem ? (
                      <div className="max-w-[80%]">
                        <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-lg rounded-br-none px-3 py-2">
                          <p className="text-[#64748b] text-xs whitespace-pre-wrap">{log}</p>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="w-7 h-7 bg-[#165DFF] rounded-lg flex items-center justify-center flex-shrink-0">
                          <Bot className="w-3.5 h-3.5 text-white" />
                        </div>
                        <div className="max-w-[80%]">
                          <div className={`rounded-lg rounded-bl-none px-3 py-2 border ${isError ? 'bg-red-50 border-red-200' : 'bg-[#f8fafc] border-[#e2e8f0]'}`}>
                            <p className={`text-xs whitespace-pre-wrap ${isError ? 'text-[#ef4444]' : 'text-[#64748b]'}`}>
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
        <div className="p-4 border-t border-[#e2e8f0] bg-white">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-2.5">
              <div className="flex-1 space-y-2">
                {/* 实时日志标签 */}
                <div className="flex items-center gap-3">
                  <span className="text-[#64748b] text-xs font-medium">实时日志</span>
                  {/* 模拟模式开关 */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#64748b] text-xs">{simulateMode ? '模拟模式' : '真实模式'}</span>
                    <button
                      onClick={() => setSimulateMode(!simulateMode)}
                      className={`relative w-10 h-5.5 rounded-full transition-colors duration-200 ${
                        simulateMode ? 'bg-[#165DFF]' : 'bg-[#cbd5e1]'
                      }`}
                    >
                      <div
                        className={`absolute top-0.5 w-4.5 h-4.5 bg-white rounded-full shadow-md transition-transform duration-200 ${
                          simulateMode ? 'left-5' : 'left-0.5'
                        }`}
                      />
                    </button>
                  </div>
                  {/* 最大步骤限制 */}
                  <div className="flex items-center gap-1.5 ml-auto">
                    <span className="text-[#64748b] text-xs">最大步骤</span>
                    <input
                      type="number"
                      value={maxSteps}
                      onChange={(e) => setMaxSteps(Math.max(1, parseInt(e.target.value) || 1))}
                      min={1}
                      max={100}
                      className="w-16 px-2 py-1 bg-[#f8fafc] border border-[#e2e8f0] rounded-md text-[#0f172a] text-xs text-center focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all"
                    />
                  </div>
                </div>
                {/* 输入框 */}
                <div className="bg-[#f8fafc] border border-[#e2e8f0] rounded-lg p-3 focus-within:border-[#165DFF] focus-within:ring-1 focus-within:ring-[#165DFF] transition-all">
                  <textarea
                    value={taskDescription}
                    onChange={(e) => setTaskDescription(e.target.value)}
                    placeholder="输入自然语言指令，AI Agent 将自动执行..."
                    className="w-full bg-transparent text-[#0f172a] text-sm resize-none focus:outline-none placeholder-[#94a3b8]"
                    rows={3}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleExecute();
                      }
                    }}
                  />
                </div>
              </div>
              <button
                onClick={handleExecute}
                disabled={!taskDescription.trim() || executionPhase === 'executing'}
                className={`px-5 py-3 rounded-lg font-medium flex items-center gap-2 transition-all duration-200 ${
                  executionPhase === 'executing'
                    ? 'bg-[#165DFF] text-white'
                    : 'bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 text-white'
                }`}
              >
                {executionPhase === 'executing' ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                {executionPhase === 'executing' ? '执行中' : '发送'}
              </button>
            </div>
            <p className="text-[#94a3b8] text-xs mt-2 text-right">按 Enter 发送，Shift+Enter 换行</p>
          </div>
        </div>
      </div>

      {/* 右侧：设备实时预览 */}
      <div className="w-80 flex flex-col bg-white border border-[#e2e8f0] rounded-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#e2e8f0]">
          <div className="flex items-center gap-2.5">
            {selectedDevice ? (
              <>
                <div className="w-7 h-7 bg-[#22c55e] rounded-lg flex items-center justify-center">
                  <Smartphone className="w-3.5 h-3.5 text-white" />
                </div>
                <div>
                  <span className="text-[#0f172a] text-xs font-medium">
                    {getSelectedDeviceInfo()?.name}
                  </span>
                  <p className="text-[#64748b] text-xs">实时预览</p>
                </div>
              </>
            ) : (
              <span className="text-[#64748b] text-xs">请选择设备</span>
            )}
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 bg-[#22c55e] rounded-full" />
            <span className="text-[#22c55e] text-xs font-medium">在线</span>
          </div>
        </div>

        <div className="flex-1 p-3">
          {selectedDevice ? (
            <div className="relative bg-[#0f172a] rounded-[1.5rem] shadow-lg aspect-[9/16] overflow-hidden border-3 border-slate-700">
              <ScrcpyPlayer
                deviceId={selectedDevice}
                enableControl={true}
                onTapSuccess={() => console.log('Tap success')}
                onTapError={(error) => console.error('Tap error:', error)}
                onSwipeSuccess={() => console.log('Swipe success')}
                onSwipeError={(error) => console.error('Swipe error:', error)}
              />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-28 h-5 bg-[#0f172a] rounded-b-xl z-20" />
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-16 h-1 bg-slate-600 rounded-full z-20" />
            </div>
          ) : (
            <div className="h-full bg-[#f8fafc] rounded-lg flex items-center justify-center border border-[#e2e8f0]">
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mx-auto mb-3">
                  <Smartphone className="w-6 h-6 text-[#165DFF]" />
                </div>
                <p className="text-[#64748b] text-xs">选择设备以查看预览</p>
                <p className="text-[#94a3b8] text-xs mt-1">自动连接 USB 设备</p>
              </div>
            </div>
          )}
        </div>

        {/* 操作提示 */}
        <div className="px-4 py-2.5 border-t border-[#e2e8f0]">
          <div className="flex items-center gap-3 text-xs text-[#64748b]">
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-4 bg-[#f8fafc] rounded-md flex items-center justify-center border border-[#e2e8f0]">
                <span className="text-[#0f172a] text-[9px] font-medium">T</span>
              </div>
              <span>点击</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-4 bg-[#f8fafc] rounded-md flex items-center justify-center border border-[#e2e8f0]">
                <span className="text-[#0f172a] text-[9px] font-medium">S</span>
              </div>
              <span>滑动</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-4 bg-[#f8fafc] rounded-md flex items-center justify-center border border-[#e2e8f0]">
                <span className="text-[#0f172a] text-[9px] font-medium">W</span>
              </div>
              <span>缩放</span>
            </div>
          </div>
        </div>

        {/* 脚本结果区域 */}
        {showScriptResult && (
          <div className="border-t border-[#e2e8f0] p-3">
            <div className="flex items-center justify-between mb-2.5">
              <h4 className="text-[#0f172a] text-xs font-medium flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-[#f59e0b]" />
                生成的脚本
              </h4>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleCopy}
                  className="p-1.5 bg-[#f8fafc] hover:bg-[#f1f5f9] rounded-lg transition-all duration-200"
                  title="复制"
                >
                  <Copy className="w-3.5 h-3.5 text-[#64748b]" />
                </button>
                <button
                  onClick={handleSaveScript}
                  className="p-1.5 bg-[#f8fafc] hover:bg-[#f1f5f9] rounded-lg transition-all duration-200"
                  title="保存"
                >
                  <Save className="w-3.5 h-3.5 text-[#64748b]" />
                </button>
                <button
                  onClick={handleDownload}
                  className="p-1.5 bg-[#f8fafc] hover:bg-[#f1f5f9] rounded-lg transition-all duration-200"
                  title="下载"
                >
                  <Download className="w-3.5 h-3.5 text-[#64748b]" />
                </button>
              </div>
            </div>
            <div className="bg-[#0f172a] rounded-lg overflow-hidden max-h-40 overflow-y-auto border border-[#334155]">
              <SyntaxHighlighterComponent
                language={getLanguage(activeTab)}
                style={customDarkStyle}
                customStyle={{ height: '100%', margin: 0, maxHeight: '160px' }}
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