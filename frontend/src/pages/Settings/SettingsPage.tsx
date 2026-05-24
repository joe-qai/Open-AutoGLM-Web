import { useEffect, useState } from 'react';
import { Settings, Server, Key, Globe, Plus, Trash2, Edit2, Check, Save, X, Bot, Zap } from 'lucide-react';
import { useModelConfigStore, type ModelConfig } from '../../stores/modelConfigStore';
import { modelConfigApi } from '../../services/api';

export function SettingsPage() {
  const { configs, fetchConfigs, createConfig, updateConfig, deleteConfig } = useModelConfigStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ModelConfig | null>(null);
  
  // Form State
  const [name, setName] = useState('');
  const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [isDefault, setIsDefault] = useState(false);

  useEffect(() => {
    fetchConfigs();
  }, []);

  const [testStatus, setTestStatus] = useState<{
    loading: boolean;
    success?: boolean;
    message?: string;
  }>({ loading: false });

  const handleTestConnection = async () => {
    if (testStatus.loading) return;
    setTestStatus({ loading: true });
    try {
      const res: any = await modelConfigApi.testConfig({
        name: name || 'test',
        provider,
        base_url: baseUrl || undefined,
        api_key: apiKey,
        model_name: modelName,
        is_default: false,
      });
      setTestStatus({
        loading: false,
        success: res.success,
        message: res.success
          ? `连接成功 (${res.response_time_ms}ms)`
          : res.message,
      });
    } catch (err: any) {
      setTestStatus({
        loading: false,
        success: false,
        message: err?.response?.data?.detail || '网络请求失败',
      });
    }
  };

  const resetForm = () => {
    setName('');
    setProvider('openai');
    setBaseUrl('');
    setApiKey('');
    setModelName('');
    setIsDefault(false);
    setEditingConfig(null);
  };

  const handleOpenModal = (config?: ModelConfig) => {
    if (config) {
      setEditingConfig(config);
      setName(config.name);
      setProvider(config.provider);
      setBaseUrl(config.base_url || '');
      setApiKey(config.api_key);
      setModelName(config.model_name);
      setIsDefault(config.is_default);
    } else {
      resetForm();
    }
    setTestStatus({ loading: false });
    setIsModalOpen(true);
  };

  const handleSubmit = async () => {
    const data = {
      name,
      provider,
      base_url: baseUrl || undefined,
      api_key: apiKey,
      model_name: modelName,
      is_default: isDefault,
    };

    try {
      if (editingConfig) {
        await updateConfig(editingConfig.config_id, data);
      } else {
        await createConfig(data as any);
      }
      setIsModalOpen(false);
      resetForm();
    } catch (error) {
      console.error('Failed to save model config:', error);
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Settings className="w-6 h-6 text-indigo-400" />
            系统设置
          </h1>
          <p className="text-[#94a3b8] mt-1">配置模型参数和多模型管理</p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <Plus className="w-4 h-4" />
          新增模型配置
        </button>
      </div>

      {/* Model Config List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {configs.map((config) => (
          <div key={config.config_id} className="bg-[#1e293b] border border-[#334155] rounded-xl p-6 relative overflow-hidden group">
            {config.is_default && (
              <div className="absolute top-0 right-0 px-3 py-1 bg-indigo-500 text-white text-[10px] font-bold rounded-bl-lg flex items-center gap-1">
                <Check className="w-3 h-3" />
                默认
              </div>
            )}
            
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 ${config.provider === 'openai' ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400'} rounded-lg flex items-center justify-center`}>
                  {config.provider === 'openai' ? <Bot className="w-5 h-5" /> : <Zap className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-white font-semibold">{config.name}</h3>
                  <p className="text-[#64748b] text-xs uppercase tracking-wider">{config.provider}</p>
                </div>
              </div>
              <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => handleOpenModal(config)}
                  className="p-2 text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors"
                  title="编辑"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    if (confirm('确定要删除此模型配置吗？')) {
                      deleteConfig(config.config_id);
                    }
                  }}
                  className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <Server className="w-4 h-4 text-[#475569]" />
                <span className="text-[#94a3b8]">模型:</span>
                <span className="text-[#e2e8f0]">{config.model_name}</span>
              </div>
              {config.base_url && (
                <div className="flex items-center gap-2 text-sm">
                  <Globe className="w-4 h-4 text-[#475569]" />
                  <span className="text-[#94a3b8]">地址:</span>
                  <span className="text-[#e2e8f0] truncate max-w-[200px]">{config.base_url}</span>
                </div>
              )}
              <div className="flex items-center gap-2 text-sm">
                <Key className="w-4 h-4 text-[#475569]" />
                <span className="text-[#94a3b8]">API Key:</span>
                <span className="text-[#e2e8f0]">••••••••••••</span>
              </div>
            </div>
          </div>
        ))}

        {configs.length === 0 && (
          <div className="col-span-full bg-[#1e293b] border border-[#334155] border-dashed rounded-xl py-12 flex flex-col items-center justify-center text-center">
            <Server className="w-12 h-12 text-[#334155] mb-4" />
            <h3 className="text-white font-medium mb-1">暂无模型配置</h3>
            <p className="text-[#64748b] text-sm mb-6">创建一个模型配置以开始使用 Agent</p>
            <button
              onClick={() => handleOpenModal()}
              className="px-4 py-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-600/30 rounded-lg transition-colors text-sm"
            >
              立即新增
            </button>
          </div>
        )}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#1e293b] border border-[#334155] rounded-2xl w-full max-w-lg shadow-2xl animate-in zoom-in duration-200">
            <div className="flex items-center justify-between p-6 border-b border-[#334155]">
              <h2 className="text-xl font-bold text-white">
                {editingConfig ? '编辑模型配置' : '新增模型配置'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-2 hover:bg-[#334155] rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-[#94a3b8]" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[#94a3b8] text-sm mb-2">配置名称</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                    placeholder="例如: GPT-4o"
                  />
                </div>
                <div>
                  <label className="block text-[#94a3b8] text-sm mb-2">Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value as any)}
                    className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">模型名称</label>
                <input
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="例如: gpt-4o 或 claude-3-5-sonnet-20240620"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">API Base URL (选填)</label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="例如: https://api.openai.com/v1"
                />
              </div>

              <div>
                <label className="block text-[#94a3b8] text-sm mb-2">API Key</label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500"
                  placeholder="输入您的 API Key"
                />
              </div>

              <div className="flex items-center gap-3 py-2">
                <button
                  onClick={() => setIsDefault(!isDefault)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${isDefault ? 'bg-indigo-600' : 'bg-[#334155]'}`}
                >
                  <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${isDefault ? 'left-6' : 'left-1'}`} />
                </button>
                <span className="text-[#e2e8f0] text-sm">设置为默认配置</span>
              </div>
            </div>

            <div className="flex gap-3 p-6 pt-0">
              <button
                onClick={handleTestConnection}
                disabled={!name || !apiKey || !modelName || testStatus.loading}
                className={`px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm ${
                  testStatus.success !== undefined
                    ? testStatus.success
                      ? 'bg-green-600/20 text-green-400 border border-green-600/30'
                      : 'bg-red-600/20 text-red-400 border border-red-600/30'
                    : 'bg-[#1e293b] border border-[#334155] text-[#94a3b8] hover:bg-[#334155] hover:text-white'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {testStatus.loading ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : testStatus.success === true ? (
                  <Check className="w-4 h-4" />
                ) : testStatus.success === false ? (
                  <X className="w-4 h-4" />
                ) : null}
                {testStatus.loading ? '测试中...' : testStatus.message || '测试连接'}
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!name || !apiKey || !modelName}
                className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
              >
                <Save className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
