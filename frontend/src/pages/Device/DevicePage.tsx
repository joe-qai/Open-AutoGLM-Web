import { useEffect } from 'react';
import {
  Smartphone,
  Power,
  Monitor,
  Wifi,
  AlertCircle,
  CheckCircle,
  Loader2,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { useDeviceStore } from '../../stores/deviceStore';
import { DeviceDetailDrawer } from '../../components/DeviceDetailDrawer';

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string; label: string; dot: string }> = {
    connected: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: '空闲', dot: 'bg-emerald-500 animate-pulse' },
    disconnected: { bg: 'bg-slate-100', text: 'text-slate-500', label: '未连接', dot: 'bg-slate-400' },
    busy: { bg: 'bg-amber-50', text: 'text-amber-600', label: '测试中', dot: 'bg-amber-500 animate-pulse' },
    error: { bg: 'bg-red-50', text: 'text-red-600', label: '错误', dot: 'bg-red-500 animate-pulse' },
  };

  const c = config[status] || config.disconnected;

  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border ${c.bg} ${c.text} border-current/20`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </div>
  );
}

function ConnectionBadge({ type, ip }: { type?: string; ip?: string }) {
  if (type === 'usb') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-600 border border-blue-100">
        <Zap size={10} /> USB
      </span>
    );
  }
  if (type === 'tcpip') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-600 border border-emerald-100">
        <Wifi size={10} /> TCP/IP
        {ip && <span className="font-mono opacity-70">{ip}</span>}
      </span>
    );
  }
  return null;
}

export function DevicePage() {
  const {
    devices,
    fetchDevices,
    connectDevice,
    disconnectDevice,
    enableWireless,
    enablingWirelessDeviceId,
    openDrawer,
    error,
    success,
    clearMessages,
  } = useDeviceStore();

  useEffect(() => {
    fetchDevices();
  }, []);

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => clearMessages(), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success, clearMessages]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'android':
        return '#22c55e';
      case 'ios':
        return '#334155';
      case 'harmonyos':
        return '#3b82f6';
      default:
        return '#64748b';
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Smartphone size={20} className="text-indigo-500" />
            <span className="text-sm font-medium text-indigo-500">设备管理</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900">设备列表</h1>
          <p className="text-slate-500 mt-1 flex items-center gap-2">
            已连接 {devices.filter((d) => d.status === 'connected').length} 台设备
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <RefreshCw size={12} className="animate-spin" />
              自动刷新
            </span>
          </p>
        </div>
        <button
          onClick={fetchDevices}
          className="btn btn-secondary"
          title="刷新设备"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {error && (
        <div
          className="mb-4 p-4 rounded-xl flex items-center gap-3 border"
          style={{
            background: 'rgba(239, 68, 68, 0.05)',
            borderColor: 'rgba(239, 68, 68, 0.15)',
          }}
        >
          <AlertCircle size={18} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {success && (
        <div
          className="mb-4 p-4 rounded-xl flex items-center gap-3 border"
          style={{
            background: 'rgba(34, 197, 94, 0.05)',
            borderColor: 'rgba(34, 197, 94, 0.15)',
          }}
        >
          <CheckCircle size={18} className="text-emerald-500 flex-shrink-0" />
          <p className="text-sm text-emerald-700">{success}</p>
        </div>
      )}

      {enablingWirelessDeviceId && (
        <div
          className="mb-4 p-4 rounded-xl flex items-center gap-3 border"
          style={{
            background: 'rgba(59, 130, 246, 0.05)',
            borderColor: 'rgba(59, 130, 246, 0.15)',
          }}
        >
          <Loader2 size={18} className="text-blue-500 animate-spin flex-shrink-0" />
          <p className="text-sm text-blue-700">
            正在为设备{' '}
            {devices.find((d) => d.device_id === enablingWirelessDeviceId)?.name ||
              enablingWirelessDeviceId}{' '}
            开启无线连接...
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {devices.map((device) => (
          <div
            key={device.device_id}
            className="rounded-xl p-5 transition-all duration-300 hover:scale-[1.02] cursor-pointer group"
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
            }}
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{
                    background: `${getPlatformColor(device.platform)}10`,
                    border: `1px solid ${getPlatformColor(device.platform)}20`,
                  }}
                >
                  <Smartphone
                    size={24}
                    style={{ color: getPlatformColor(device.platform) }}
                  />
                </div>
                <div>
                  <h3 className="text-slate-900 font-semibold">{device.name}</h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {device.platform === 'android'
                      ? 'Android'
                      : device.platform === 'ios'
                      ? 'iOS'
                      : device.platform === 'harmonyos'
                      ? 'HarmonyOS'
                      : device.platform}
                  </p>
                </div>
              </div>
              <StatusBadge status={device.status} />
            </div>

            <div className="flex flex-wrap gap-2 mb-4">
              {device.os_version && (
                <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  {device.os_version}
                </span>
              )}
              {device.screen_width && device.screen_height && (
                <span className="px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
                  {device.screen_width}x{device.screen_height}
                </span>
              )}
              <ConnectionBadge type={device.connection_type} ip={device.ip} />
            </div>

            <div className="flex gap-2 pt-3 border-t border-slate-200" style={{ borderColor: '#e2e8f0' }}>
              {device.status === 'disconnected' ? (
                <button
                  onClick={() => connectDevice(device.device_id)}
                  className="flex-1 btn btn-success"
                >
                  <Power size={14} />
                  连接设备
                </button>
              ) : device.status === 'busy' ? (
                <button disabled className="flex-1 btn" style={{ background: '#f59e0b15', color: '#f59e0b', border: '1px solid #f59e0b25' }}>
                  <Loader2 size={14} className="animate-spin" />
                  测试中
                </button>
              ) : (
                <>
                  {device.connection_type !== 'tcpip' && (
                    <button
                      onClick={() => enableWireless(device.device_id)}
                      disabled={enablingWirelessDeviceId === device.device_id}
                      className="flex-1 btn btn-primary"
                      title={enablingWirelessDeviceId === device.device_id ? '开启中...' : '开启无线'}
                    >
                      <Wifi size={14} />
                    </button>
                  )}
                  {device.connection_type === 'tcpip' && (
                    <button
                      onClick={() => disconnectDevice(device.device_id)}
                      className="flex-1 btn btn-danger"
                      title="断开连接"
                    >
                      <Power size={14} />
                    </button>
                  )}
                </>
              )}
              <button
                onClick={() => openDrawer(device)}
                className="flex-1 btn btn-secondary"
                title="设备详情"
              >
                <Monitor size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      {devices.length === 0 && (
        <div
          className="text-center py-24 rounded-xl"
          style={{
            background: '#ffffff',
            border: '1px solid #e2e8f0',
          }}
        >
          <Smartphone size={56} className="mx-auto mb-4 text-slate-300" />
          <h3 className="text-slate-900 text-lg font-medium mb-2">暂无设备</h3>
          <p className="text-slate-500 text-sm">连接USB设备或开启无线连接即可开始使用</p>
        </div>
      )}

      <DeviceDetailDrawer />
    </div>
  );
}
