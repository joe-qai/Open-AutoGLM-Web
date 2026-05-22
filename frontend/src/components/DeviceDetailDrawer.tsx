import { useEffect } from 'react';
import { X, RefreshCw, Smartphone, Wifi, Power, Loader2, AlertCircle } from 'lucide-react';
import { useDeviceStore } from '../stores/deviceStore';

export function DeviceDetailDrawer() {
  const { selectedDevice, drawerOpen, screenshotData, loadingScreenshot, closeDrawer, connectDevice, disconnectDevice, enableWireless, enablingWirelessDeviceId } = useDeviceStore();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerOpen) {
        closeDrawer();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [drawerOpen, closeDrawer]);

  if (!drawerOpen || !selectedDevice) return null;

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
        return <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">在线</span>;
      case 'disconnected':
        return <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">离线</span>;
      case 'busy':
        return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">忙碌</span>;
      default:
        return null;
    }
  };

  const handleRefreshScreenshot = () => {
    if (selectedDevice) {
      useDeviceStore.getState().openDrawer(selectedDevice);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={closeDrawer}
      />

      {/* Drawer Panel */}
      <div className="fixed right-0 top-0 h-full w-[400px] bg-[#1e293b] border-l border-[#334155] z-50 animate-slide-in-right overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#334155]">
          <div className="flex items-center gap-3">
            <Smartphone className="w-5 h-5 text-indigo-400" />
            <h2 className="text-white font-medium text-lg">{selectedDevice.name}</h2>
            {getPlatformIcon(selectedDevice.platform)}
            <span className="text-[#94a3b8] text-sm capitalize">{selectedDevice.platform}</span>
            {getStatusBadge(selectedDevice.status)}
          </div>
          <button
            onClick={closeDrawer}
            className="p-1 rounded-lg hover:bg-[#334155] text-[#64748b] hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Device Info Section */}
        <div className="p-4 border-b border-[#334155]">
          <h3 className="text-[#94a3b8] text-sm font-medium mb-3">设备信息</h3>
          <div className="space-y-2 text-sm">
            {selectedDevice.model && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">型号</span>
                <span className="text-[#94a3b8]">{selectedDevice.model}</span>
              </div>
            )}
            {selectedDevice.manufacturer && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">制造商</span>
                <span className="text-[#94a3b8]">{selectedDevice.manufacturer}</span>
              </div>
            )}
            {selectedDevice.os_version && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">系统版本</span>
                <span className="text-[#94a3b8]">{selectedDevice.os_version}</span>
              </div>
            )}
            {selectedDevice.device_type && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">设备类型</span>
                <span className="text-[#94a3b8]">{selectedDevice.device_type}</span>
              </div>
            )}
            {selectedDevice.android_sdk_version && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">SDK版本</span>
                <span className="text-[#94a3b8]">{selectedDevice.android_sdk_version}</span>
              </div>
            )}
            {selectedDevice.screen_width && selectedDevice.screen_height && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">分辨率</span>
                <span className="text-[#94a3b8]">{selectedDevice.screen_width}x{selectedDevice.screen_height}</span>
              </div>
            )}
            {selectedDevice.connection_type && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">连接方式</span>
                <span className="text-[#94a3b8]">{selectedDevice.connection_type === 'usb' ? 'USB' : '无线'}</span>
              </div>
            )}
            {selectedDevice.ip && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">IP地址</span>
                <span className="text-[#94a3b8]">{selectedDevice.ip}</span>
              </div>
            )}
            {selectedDevice.battery_level !== undefined && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">电量</span>
                <span className="text-[#94a3b8]">{selectedDevice.battery_level}%</span>
              </div>
            )}
            {selectedDevice.last_seen && (
              <div className="flex justify-between">
                <span className="text-[#64748b]">最后在线</span>
                <span className="text-[#94a3b8]">{selectedDevice.last_seen}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-[#64748b]">设备ID</span>
              <span className="text-[#94a3b8] font-mono">{selectedDevice.device_id}</span>
            </div>
          </div>
        </div>

        {/* Screenshot Section */}
        <div className="p-4 border-b border-[#334155]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[#94a3b8] text-sm font-medium">实时截图</h3>
            {screenshotData && (
              <button
                onClick={handleRefreshScreenshot}
                className="p-1 rounded-lg hover:bg-[#334155] text-[#64748b] hover:text-white transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}
          </div>
          {loadingScreenshot ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
            </div>
          ) : screenshotData ? (
            <img
              src={`data:image/png;base64,${screenshotData}`}
              alt="Device screenshot"
              className="w-full rounded-lg border border-[#334155]"
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-[#64748b]">
              <AlertCircle className="w-6 h-6 mb-2" />
              <span className="text-sm">截图获取失败</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="p-4">
          <div className="flex gap-2">
            {selectedDevice.status === 'disconnected' ? (
              <button
                onClick={() => connectDevice(selectedDevice.device_id)}
                className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Power className="w-4 h-4" />
                连接
              </button>
            ) : (
              <>
                  <button
                    onClick={() => enableWireless(selectedDevice.device_id)}
                    disabled={enablingWirelessDeviceId === selectedDevice.device_id}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Wifi className="w-4 h-4" />
                    {enablingWirelessDeviceId === selectedDevice.device_id ? '开启中...' : '开启无线'}
                  </button>
                <button
                  onClick={() => disconnectDevice(selectedDevice.device_id)}
                  className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Power className="w-4 h-4" />
                  断开
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}