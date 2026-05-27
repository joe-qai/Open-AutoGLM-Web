import { useEffect } from 'react';
import { Smartphone, Search, Power, Monitor, Wifi, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { useDeviceStore } from '../../stores/deviceStore';
import { DeviceDetailDrawer } from '../../components/DeviceDetailDrawer';

export function DevicePage() {
  const { devices, fetchDevices, connectDevice, disconnectDevice, enableWireless, enablingWirelessDeviceId, openDrawer, error, success, clearMessages } = useDeviceStore();

  useEffect(() => {
    fetchDevices();
  }, []);

  useEffect(() => {
    if (error || success) {
      const timer = setTimeout(() => clearMessages(), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, success, clearMessages]);

  // Auto-scan every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDevices]);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'android':
        return <div className="w-3 h-3 rounded-full bg-[#3ddc84]" />;
      case 'ios':
        return <div className="w-3 h-3 rounded-full bg-white" />;
      case 'harmonyos':
        return <div className="w-3 h-3 rounded-full bg-[#007dff]" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-400 animate-pulse"></span>
            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">空闲</span>
          </div>
        );
      case 'disconnected':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-gray-400"></span>
            <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">未初始化</span>
          </div>
        );
      case 'busy':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 animate-pulse"></span>
            <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">忙碌</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400 animate-pulse"></span>
            <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">错误</span>
          </div>
        );
      default:
        return null;
    }
  };

  const getConnectionBadge = (connectionType?: string, ip?: string) => {
    switch (connectionType) {
      case 'usb':
        return (
          <div className="flex items-center gap-1">
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded-full">
              USB
            </span>
          </div>
        );
      case 'tcpip':
        return (
          <div className="flex items-center gap-1">
            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">
              TCP/IP
            </span>
            {ip && (
              <span className="text-[#64748b] text-xs">{ip}</span>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Smartphone className="w-6 h-6 text-indigo-400" />
            设备管理
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <p className="text-[#94a3b8]">管理您的测试设备</p>
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
              自动扫描已开启
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={fetchDevices}
            className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Search className="w-4 h-4" />
            扫描设备
          </button>
        </div>
      </div>

      {/* Messages */}
      {enablingWirelessDeviceId && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-500/30 rounded-lg flex items-center gap-2 text-blue-300">
          <Loader2 className="w-4 h-4 animate-spin" />
          正在为设备 {devices.find(d => d.device_id === enablingWirelessDeviceId)?.name || enablingWirelessDeviceId} 开启无线连接...
        </div>
      )}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-300">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 bg-green-900/30 border border-green-500/30 rounded-lg flex items-center gap-2 text-green-300">
          <CheckCircle className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Device Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map((device) => (
          <div
            key={device.device_id}
            className="bg-gradient-to-br from-slate-800/80 to-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-5 hover:border-slate-600/50 hover:shadow-xl hover:shadow-indigo-500/5 transition-all duration-300"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-white font-semibold text-lg">{device.name}</h3>
                <p className="text-slate-400 text-sm mt-1">
                  {device.platform === 'android' ? 'Android' : device.platform === 'ios' ? 'iOS' : device.platform === 'harmonyos' ? 'HarmonyOS' : device.platform} {device.os_version} · {device.model}
                </p>
              </div>
              {getStatusBadge(device.status)}
            </div>

            <div className="flex flex-wrap gap-2 mb-4">
              {device.os_version && (
                <span className="px-3 py-1.5 bg-slate-700/50 text-slate-300 text-xs rounded-lg">
                  {device.os_version}
                </span>
              )}
              {device.screen_width && device.screen_height && (
                <span className="px-3 py-1.5 bg-slate-700/50 text-slate-300 text-xs rounded-lg">
                  {device.screen_width}x{device.screen_height}
                </span>
              )}
              {device.connection_type === 'usb' && (
                <span className="px-3 py-1.5 bg-blue-500/20 text-blue-400 text-xs rounded-lg flex items-center gap-1">
                  <Wifi className="w-3 h-3" />
                  USB
                </span>
              )}
              {device.connection_type === 'tcpip' && (
                <span className="px-3 py-1.5 bg-green-500/20 text-green-400 text-xs rounded-lg flex items-center gap-1">
                  <Wifi className="w-3 h-3" />
                  TCP/IP
                </span>
              )}
              {device.ip && (
                <span className="px-3 py-1.5 bg-slate-700/50 text-slate-400 text-xs rounded-lg font-mono">
                  {device.ip}
                </span>
              )}
            </div>

            <div className="flex gap-2">
              {device.status === 'disconnected' ? (
                <button
                  onClick={() => connectDevice(device.device_id)}
                  className="flex-1 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-green-500/20"
                >
                  <Power className="w-4 h-4" />
                  连接
                </button>
              ) : device.status === 'busy' ? (
                <button
                  disabled
                  className="flex-1 py-3 bg-gradient-to-r from-yellow-600 to-orange-600 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 opacity-70"
                >
                  <Loader2 className="w-4 h-4 animate-spin" />
                  测试中
                </button>
              ) : (
                <>
                  {device.connection_type !== 'tcpip' && (
                    <button
                      onClick={() => enableWireless(device.device_id)}
                      disabled={enablingWirelessDeviceId === device.device_id}
                      className="flex-1 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-indigo-500/20"
                    >
                      <Wifi className="w-4 h-4" />
                      {enablingWirelessDeviceId === device.device_id ? '开启中...' : '开启无线'}
                    </button>
                  )}
                  {device.connection_type === 'tcpip' && (
                    <button
                      onClick={() => disconnectDevice(device.device_id)}
                      className="flex-1 py-3 bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all duration-200 shadow-lg shadow-red-500/20"
                    >
                      <Power className="w-4 h-4" />
                      断开
                    </button>
                  )}
                </>
              )}
              <button
                onClick={() => openDrawer(device)}
                className="flex-1 py-3 bg-slate-700/50 hover:bg-slate-600/50 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-all duration-200"
              >
                <Monitor className="w-4 h-4" />
                详情
              </button>
            </div>
          </div>
        ))}
      </div>

      {devices.length === 0 && (
        <div className="text-center py-20">
          <Smartphone className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无设备</h3>
          <p className="text-[#64748b] mb-4">连接USB设备即可开始使用</p>
        </div>
      )}
      <DeviceDetailDrawer />
    </div>
  );
}
