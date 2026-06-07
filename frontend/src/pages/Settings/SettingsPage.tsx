import { useEffect, useState } from 'react';
import { Settings, Server, Key, Globe, Plus, Trash2, Edit2, Check, Save, X, Bot, Zap, Eye, EyeOff } from 'lucide-react';
import { useModelConfigStore, type ModelConfig } from '../../stores/modelConfigStore';
import { modelConfigApi } from '../../services/api';

export function SettingsPage() {
  const { configs, fetchConfigs, createConfig, updateConfig, deleteConfig } = useModelConfigStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ModelConfig | null>(null);
  
  const [name, setName] = useState('');
  const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [modelName, setModelName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [pageToast, setPageToast] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [testLoading, setTestLoading] = useState(false);
  const [cardTestId, setCardTestId] = useState<string | null>(null);

  useEffect(() => {
    fetchConfigs();
  }, []);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  useEffect(() => {
    if (pageToast) {
      const timer = setTimeout(() => setPageToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [pageToast]);

  const handleTestConnection = async () => {
    if (testLoading) return;
    setTestLoading(true);
    try {
      const res: any = await modelConfigApi.testConfig({
        name: name || 'test',
        provider,
        base_url: baseUrl || undefined,
        api_key: apiKey,
        model_name: modelName,
        is_default: false,
      });
      setTestLoading(false);
      if (res.success) {
        setToast({ type: 'success', text: `连接成功 (${res.response_time_ms}ms)` });
      } else {
        setToast({ type: 'error', text: res.message });
      }
    } catch (err: any) {
      setTestLoading(false);
      setToast({ type: 'error', text: err?.response?.data?.detail || '网络请求失败' });
    }
  };

  const handleCardTestConnection = async (config: ModelConfig) => {
    if (cardTestId) return;
    setCardTestId(config.config_id);
    try {
      const res: any = await modelConfigApi.testConfig({
        name: config.name,
        provider: config.provider,
        base_url: config.base_url || undefined,
        api_key: config.api_key,
        model_name: config.model_name,
        is_default: false,
      });
      setCardTestId(null);
      setPageToast({
        type: res.success ? 'success' : 'error',
        text: res.success ? `连接成功 (${res.response_time_ms}ms)` : res.message,
      });
    } catch (err: any) {
      setCardTestId(null);
      setPageToast({ type: 'error', text: err?.response?.data?.detail || '网络请求失败' });
    }
  };

  const resetForm = () => {
    setName('');
    setProvider('openai');
    setBaseUrl('');
    setApiKey('');
    setModelName('');
    setIsDefault(false);
    setShowApiKey(false);
    setToast(null);
    setTestLoading(false);
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
    setToast(null);
    setTestLoading(false);
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
      {pageToast && (
        <div className={`mb-4 p-3 rounded-lg flex items-center gap-2 text-sm ${
          pageToast.type === 'success'
            ? 'bg-green-50 border border-green-200 text-green-700'
            : 'bg-red-50 border border-red-200 text-red-700'
        }`}>
          {pageToast.type === 'success' ? <Check className="w-4 h-4 shrink-0" /> : <X className="w-4 h-4 shrink-0" />}
          {pageToast.text}
        </div>
      )}

      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-semibold text-[#0f172a] flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#165DFF]" />
            模型配置
          </h1>
          <p className="text-[#64748b] text-sm mt-1">配置VLM视觉模型参数</p>
        </div>
        <button
          onClick={() => handleOpenModal()}
          className="px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] text-white rounded-lg flex items-center gap-2 transition-all duration-200"
        >
          <Plus className="w-4 h-4" />
          新增模型配置
        </button>
      </div>

      <div className="mb-6 p-4 bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
          <Zap className="w-4 h-4 text-amber-600" />
        </div>
        <div>
          <h3 className="font-medium text-amber-800 mb-1">重要提示</h3>
          <p className="text-amber-700 text-sm">
            当前项目基于 <span className="font-semibold">VLM 视觉大模型</span> 驱动的 Phone Agent。
            请确保配置支持视觉能力的模型（如 GPT-4V、Claude 3.5 Sonnet 等），否则将无法正常使用智能体功能。
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {configs.map((config) => (
          <div
            key={config.config_id}
            className="bg-white border border-[#e2e8f0] rounded-lg p-4 hover:border-[#165DFF] hover:shadow-md transition-all duration-200 relative"
          >
            {config.is_default && (
              <div className="absolute top-2 right-2 px-2 py-0.5 bg-[#165DFF] text-white text-xs font-medium rounded flex items-center gap-1">
                <Check className="w-3 h-3" />
                默认
              </div>
            )}
            
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className={`w-10 h-10 ${config.provider === 'openai' ? 'bg-[#e8f0fe]' : 'bg-[#fff3e0]'} rounded-lg flex items-center justify-center shrink-0`}>
                  {config.provider === 'openai' ? <Bot className="w-5 h-5 text-[#165DFF]" /> : <Zap className="w-5 h-5 text-[#f59e0b]" />}
                </div>
                <div>
                  <h3 className="text-[#0f172a] font-medium text-sm">{config.name}</h3>
                  <p className="text-[#94a3b8] text-xs uppercase">{config.provider}</p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleCardTestConnection(config)}
                  disabled={cardTestId !== null}
                  className="p-1.5 text-[#22c55e] hover:bg-[#dcfce7] rounded-lg transition-all duration-200 disabled:opacity-50"
                  title="测试连接"
                >
                  {cardTestId === config.config_id ? (
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <Zap className="w-4 h-4" />
                  )}
                </button>
                <button
                  onClick={() => handleOpenModal(config)}
                  className="p-1.5 text-[#94a3b8] hover:text-[#165DFF] hover:bg-[#e8f0fe] rounded-lg transition-all duration-200"
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
                  className="p-1.5 text-[#94a3b8] hover:text-[#ef4444] hover:bg-[#fef2f2] rounded-lg transition-all duration-200"
                  title="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="space-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                <Server className="w-3.5 h-3.5 text-[#94a3b8] shrink-0" />
                <span className="text-[#94a3b8] shrink-0 w-10">模型:</span>
                <span className="text-[#0f172a] truncate">{config.model_name}</span>
              </div>
              {config.base_url && (
                <div className="flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-[#94a3b8] shrink-0" />
                  <span className="text-[#94a3b8] shrink-0 w-10">地址:</span>
                  <span className="text-[#0f172a] truncate">{config.base_url}</span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Key className="w-3.5 h-3.5 text-[#94a3b8] shrink-0" />
                <span className="text-[#94a3b8] shrink-0 w-10">API Key:</span>
                <span className="text-[#64748b] font-mono">••••••••</span>
              </div>
            </div>
          </div>
        ))}

        {configs.length === 0 && (
          <div className="col-span-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-16 flex flex-col items-center justify-center text-center">
            <Server className="w-12 h-12 text-[#94a3b8] mb-3" />
            <h3 className="text-[#0f172a] text-base font-medium mb-1.5">暂无模型配置</h3>
            <p className="text-[#64748b] text-sm">创建一个模型配置以开始使用 Agent</p>
          </div>
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white border border-[#e2e8f0] rounded-lg w-full max-w-lg shadow-lg">
            <div className="flex items-center justify-between p-5 border-b border-[#f1f5f9]">
              <h2 className="text-base font-semibold text-[#0f172a]">
                {editingConfig ? '编辑模型配置' : '新增模型配置'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="p-1.5 hover:bg-[#f1f5f9] rounded-lg transition-all duration-200"
              >
                <X className="w-4 h-4 text-[#64748b]" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#64748b] text-sm mb-2">配置名称</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                    placeholder="例如: GPT-4o"
                  />
                </div>
                <div>
                  <label className="block text-[#64748b] text-sm mb-2">Provider</label>
                  <select
                    value={provider}
                    onChange={(e) => setProvider(e.target.value as any)}
                    className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  >
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[#64748b] text-sm mb-2">模型名称</label>
                <input
                  type="text"
                  value={modelName}
                  onChange={(e) => setModelName(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  placeholder="例如: gpt-4o"
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-sm mb-2">
                  API Base URL <span className="text-[#ef4444]">*</span>
                </label>
                <input
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 px-3 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                  placeholder="例如: https://api.openai.com/v1"
                />
              </div>

              <div>
                <label className="block text-[#64748b] text-sm mb-2">
                  API Key <span className="text-[#ef4444]">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showApiKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full bg-[#f8fafc] border border-[#e2e8f0] rounded-lg py-2.5 pl-3 pr-10 text-[#0f172a] text-sm placeholder-[#94a3b8] focus:outline-none focus:border-[#165DFF] focus:ring-1 focus:ring-[#165DFF] transition-all duration-200"
                    placeholder="输入您的 API Key"
                  />
                  <button
                    type="button"
                    onClick={() => setShowApiKey(!showApiKey)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[#94a3b8] hover:text-[#0f172a] transition-all duration-200"
                  >
                    {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-3 py-2">
                <button
                  onClick={() => setIsDefault(!isDefault)}
                  className={`w-10 h-5 rounded-full transition-all duration-200 relative ${isDefault ? 'bg-[#165DFF]' : 'bg-[#e2e8f0]'}`}
                >
                  <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all duration-200 ${isDefault ? 'left-6' : 'left-1'}`} />
                </button>
                <span className="text-[#0f172a] text-sm">设置为默认配置</span>
              </div>
            </div>

            {toast && (
              <div className={`mx-5 mb-3 p-2.5 rounded-lg flex items-center gap-2 text-sm ${
                toast.type === 'success'
                  ? 'bg-[#dcfce7] border border-[#bbf7d0] text-[#166534]'
                  : 'bg-[#fee2e2] border border-[#fecaca] text-[#991b1b]'
              }`}>
                {toast.type === 'success' ? <Check className="w-4 h-4 shrink-0" /> : <X className="w-4 h-4 shrink-0" />}
                {toast.text}
              </div>
            )}
            <div className="flex gap-2 p-5 pt-0">
              <button
                onClick={handleTestConnection}
                disabled={!name || !baseUrl || !apiKey || !modelName || testLoading}
                className="px-3 py-2 rounded-lg flex items-center justify-center gap-2 text-sm bg-[#f1f5f9] border border-[#e2e8f0] text-[#64748b] hover:bg-[#e2e8f0] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
              >
                {testLoading ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : null}
                {testLoading ? '测试中...' : '测试连接'}
              </button>
              <button
                onClick={() => setIsModalOpen(false)}
                className="flex-1 px-4 py-2 bg-[#f1f5f9] hover:bg-[#e2e8f0] text-[#64748b] rounded-lg text-sm font-medium transition-all duration-200"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!name || !baseUrl || !apiKey || !modelName}
                className="flex-1 px-4 py-2 bg-[#165DFF] hover:bg-[#0f4cdb] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200"
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