# Platform UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 5 UX/functional issues: APK filename display, device auto-scan, report batch delete, log search/preview, device detail button

**Architecture:** Incremental improvements across backend and frontend. Backend adds SQLite metadata for APK, batch delete endpoint for reports. Frontend adds device drawer, auto-scan polling, server-side log search, checkbox batch delete pattern.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Zustand/TailwindCSS (frontend), SQLite (APK metadata, audit logs)

---

## File Structure

### New Files
- `backend/app/services/apk_metadata_service.py` — SQLite-backed APK metadata persistence
- `frontend/src/components/DeviceDetailDrawer.tsx` — Slide-over device detail panel

### Modified Files
- `backend/app/schemas/apk.py` — Add `original_filename` to ApkInfo
- `backend/app/services/apk_service.py` — Integrate ApkMetadataService
- `backend/app/schemas/report.py` — Add BatchDeleteRequest, BatchDeleteResponse
- `backend/app/services/report_service.py` — Add batch_delete method
- `backend/app/api/v1/reports.py` — Add batch delete endpoint
- `frontend/src/services/api.ts` — Add batchDeleteReports, update logApi params
- `frontend/src/stores/apkStore.ts` — Add original_filename to Apk interface
- `frontend/src/stores/deviceStore.ts` — Add openDrawer, closeDrawer, screenshot/apps state
- `frontend/src/stores/reportStore.ts` — Add batchDeleteReports action
- `frontend/src/pages/Apk/ApkPage.tsx` — Add original_filename column
- `frontend/src/pages/Device/DevicePage.tsx` — Auto-scan + detail drawer button
- `frontend/src/pages/Report/ReportPage.tsx` — Checkbox + batch action bar
- `frontend/src/pages/Logs/LogsPage.tsx` — Server-side search + pagination + detail display
- `frontend/src/index.css` — Add slide-in animation

---

### Task 1: APK Metadata Backend

**Files:**
- Create: `backend/app/services/apk_metadata_service.py`
- Modify: `backend/app/schemas/apk.py`
- Modify: `backend/app/services/apk_service.py`
- Modify: `frontend/src/stores/apkStore.ts`
- Modify: `frontend/src/pages/Apk/ApkPage.tsx`

- [ ] **Step 1: Add `original_filename` to ApkInfo schema**

Open `backend/app/schemas/apk.py`. Add the field to the `ApkInfo` class after the `name` field:

```python
class ApkInfo(BaseModel):
    """APK information model."""
    id: str
    name: str
    original_filename: Optional[str] = None  # User's original upload filename
    version: Optional[str] = None
    package_name: Optional[str] = None
    file_size: Optional[int] = None
    upload_time: datetime
    status: ApkStatus
    file_path: Optional[str] = None
    icon_base64: Optional[str] = None
    
    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create ApkMetadataService**

Create `backend/app/services/apk_metadata_service.py`:

```python
"""SQLite-backed APK metadata service for persisting upload info."""

import sqlite3
import time
import threading
from typing import Optional, List, Dict
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "apk_metadata.db"


class ApkMetadataService:
    """Singleton service that stores APK metadata in SQLite."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database and create tables."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apk_metadata (
                apk_id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                package_name TEXT,
                version TEXT,
                file_size INTEGER,
                upload_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'uploaded'
            )
        """)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a new SQLite connection (one per operation for thread safety)."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def save(
        self,
        apk_id: str,
        original_filename: str,
        package_name: Optional[str] = None,
        version: Optional[str] = None,
        file_size: Optional[int] = None,
        upload_time: Optional[str] = None,
        status: str = "uploaded",
    ) -> str:
        """Save APK metadata. Returns the apk_id."""
        if upload_time is None:
            upload_time = time.strftime("%Y-%m-%dT%H:%M:%S")

        conn = self._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO apk_metadata
                   (apk_id, original_filename, package_name, version, file_size, upload_time, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (apk_id, original_filename, package_name, version, file_size, upload_time, status),
            )
            conn.commit()
        finally:
            conn.close()

        return apk_id

    def get(self, apk_id: str) -> Optional[Dict]:
        """Get metadata for a single APK."""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM apk_metadata WHERE apk_id = ?", (apk_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def list_all(self) -> List[Dict]:
        """List all APK metadata entries."""
        conn = self._get_conn()
        try:
            rows = conn.execute("SELECT * FROM apk_metadata ORDER BY upload_time DESC").fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete(self, apk_id: str) -> bool:
        """Delete metadata for an APK. Returns True if found and deleted."""
        conn = self._get_conn()
        try:
            result = conn.execute(
                "DELETE FROM apk_metadata WHERE apk_id = ?", (apk_id,)
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def update_status(self, apk_id: str, status: str) -> bool:
        """Update APK status (e.g., to 'installed'). Returns True if found."""
        conn = self._get_conn()
        try:
            result = conn.execute(
                "UPDATE apk_metadata SET status = ? WHERE apk_id = ?",
                (status, apk_id),
            )
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()
```

- [ ] **Step 3: Integrate ApkMetadataService into ApkService**

Open `backend/app/services/apk_service.py`. 

Add the import at the top:
```python
from app.services.apk_metadata_service import ApkMetadataService
```

In the `__init__` method, add `self.metadata = ApkMetadataService()`:
```python
    def __init__(self):
        self.apks = {}
        self.metadata = ApkMetadataService()
        self.upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "apks")
        os.makedirs(self.upload_dir, exist_ok=True)
```

In `upload_apk`, after `apk_info_data = self._parse_apk_info(file_path)` add metadata save:
```python
            # Save metadata to SQLite for persistence
            self.metadata.save(
                apk_id=apk_id,
                original_filename=filename,
                package_name=apk_info_data.get("package_name"),
                version=apk_info_data.get("version"),
                file_size=len(content),
                upload_time=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                status="uploaded",
            )
```

Also in `upload_apk`, change the ApkInfo creation to include `original_filename`:
```python
            apk_info = ApkInfo(
                id=apk_id,
                name=filename,
                original_filename=filename,
                version=apk_info_data.get("version"),
                package_name=apk_info_data.get("package_name"),
                file_size=len(content),
                upload_time=datetime.now(),
                status=ApkStatus.UPLOADED,
                file_path=file_path
            )
```

Replace the entire `list_apks` method:
```python
    def list_apks(self) -> List[ApkInfo]:
        """List all uploaded APKs."""
        apk_list = []
        
        for filename in os.listdir(self.upload_dir):
            if filename.endswith(".apk"):
                file_path = os.path.join(self.upload_dir, filename)
                file_stat = os.stat(file_path)
                
                apk_id = os.path.splitext(filename)[0]
                apk_info = self._parse_apk_info(file_path)
                
                # Query metadata for original_filename
                meta = self.metadata.get(apk_id)
                original_filename = meta.get("original_filename") if meta else filename
                
                apk_list.append(ApkInfo(
                    id=apk_id,
                    name=filename,
                    original_filename=original_filename,
                    version=apk_info.get("version") or (meta.get("version") if meta else None),
                    package_name=apk_info.get("package_name") or (meta.get("package_name") if meta else None),
                    file_size=file_stat.st_size,
                    upload_time=datetime.fromtimestamp(file_stat.st_mtime),
                    status=ApkStatus.UPLOADED,
                    file_path=file_path
                ))
        
        return apk_list
```

In `delete_apk`, after `os.remove(apk.file_path)` add metadata deletion:
```python
            # Also delete metadata
            self.metadata.delete(apk_id)
```

- [ ] **Step 4: Update frontend Apk interface and table**

Open `frontend/src/stores/apkStore.ts`. Add `original_filename` to the `Apk` interface:
```typescript
export interface Apk {
  id: string;
  name: string;
  original_filename?: string;
  version?: string;
  package_name?: string;
  file_size?: number;
  upload_time: string;
  status: 'uploaded' | 'installed' | 'failed';
  file_path?: string;
  icon_base64?: string;
}
```

Open `frontend/src/pages/Apk/ApkPage.tsx`. Add a new table header column after "APK信息":
```tsx
<th className="px-6 py-3 text-left text-xs font-medium text-[#94a3b8] uppercase tracking-wider">
  原始文件名
</th>
```

Add a corresponding data cell in each row, after the APK info cell:
```tsx
<td className="px-6 py-4 whitespace-nowrap text-sm text-[#94a3b8]">
  {apk.original_filename || apk.name}
</td>
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/apk.py backend/app/services/apk_metadata_service.py backend/app/services/apk_service.py frontend/src/stores/apkStore.ts frontend/src/pages/Apk/ApkPage.tsx
git commit -m "feat: add original_filename to APK metadata with SQLite persistence"
```

---

### Task 2: Device Auto-Scan

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx`

- [ ] **Step 1: Add auto-scan polling and rename button**

Open `frontend/src/pages/Device/DevicePage.tsx`.

Replace `RefreshCw` with `Search` in the lucide-react imports:
```tsx
import { Smartphone, Search, Power, Monitor, Wifi, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
```

After the existing `useEffect` for messages, add auto-scan:
```tsx
  // Auto-scan every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDevices();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchDevices]);
```

Replace the subtitle paragraph with a flex container that includes the auto-scan indicator:
```tsx
          <div className="flex items-center gap-2 mt-1">
            <p className="text-[#94a3b8]">管理您的测试设备</p>
            <span className="flex items-center gap-1 text-xs text-green-400">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
              自动扫描已开启
            </span>
          </div>
```

Remove the original standalone `<p className="text-[#94a3b8] mt-1">管理您的测试设备</p>` line.

Change the button icon and text:
```tsx
          <button
            onClick={fetchDevices}
            className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Search className="w-4 h-4" />
            扫描设备
          </button>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Device/DevicePage.tsx
git commit -m "feat: add 30-second auto-scan polling and rename refresh to scan button"
```

---

### Task 3: Device Detail Drawer

**Files:**
- Create: `frontend/src/components/DeviceDetailDrawer.tsx`
- Modify: `frontend/src/stores/deviceStore.ts`
- Modify: `frontend/src/pages/Device/DevicePage.tsx`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add store actions for drawer, screenshot, and apps**

Open `frontend/src/stores/deviceStore.ts`. 

Change the import line to include the default `api` export:
```typescript
import api, { deviceApi } from '../services/api';
```

Add new state fields to `DeviceState`:
```typescript
interface DeviceState {
  devices: Device[];
  selectedDevice: Device | null;
  screenshotData: string | null;
  deviceApps: { package_name: string; name: string }[];
  loadingScreenshot: boolean;
  loadingApps: boolean;
  drawerOpen: boolean;
  loading: boolean;
  connectingTcpIp: boolean;
  enablingWireless: boolean;
  error: string | null;
  success: string | null;

  // Actions
  fetchDevices: () => Promise<void>;
  selectDevice: (device: Device | null) => void;
  openDrawer: (device: Device) => Promise<void>;
  closeDrawer: () => void;
  connectDevice: (deviceId: string) => Promise<void>;
  disconnectDevice: (deviceId: string) => Promise<void>;
  connectTcpIp: (ipPort: string) => Promise<void>;
  enableWireless: (deviceId: string, port?: number) => Promise<void>;
  getDeviceIp: (deviceId: string) => Promise<string | null>;
  clearMessages: () => void;
}
```

Add state defaults:
```typescript
  screenshotData: null,
  deviceApps: [],
  loadingScreenshot: false,
  loadingApps: false,
  drawerOpen: false,
```

Add the `openDrawer` and `closeDrawer` actions:
```typescript
  openDrawer: async (device: Device) => {
    set({ selectedDevice: device, drawerOpen: true, screenshotData: null, deviceApps: [], loadingScreenshot: true, loadingApps: true });
    try {
      const response = await deviceApi.getScreenshot(device.device_id) as unknown as { screenshot_base64: string };
      set({ screenshotData: response.screenshot_base64, loadingScreenshot: false });
    } catch {
      set({ screenshotData: null, loadingScreenshot: false });
    }
    try {
      const appsResponse = await api.get(`/api/v1/devices/${device.device_id}/apps`) as unknown as { apps: { package_name: string; name: string }[] };
      set({ deviceApps: appsResponse.apps || [], loadingApps: false });
    } catch {
      set({ deviceApps: [], loadingApps: false });
    }
  },

  closeDrawer: () => {
    set({ drawerOpen: false, screenshotData: null, deviceApps: [] });
  },
```

- [ ] **Step 2: Create DeviceDetailDrawer component**

Create `frontend/src/components/DeviceDetailDrawer.tsx`:

```tsx
import { useEffect } from 'react';
import { X, RefreshCw, Smartphone, Wifi, Power, Loader2, AlertCircle } from 'lucide-react';
import { useDeviceStore } from '../stores/deviceStore';

export function DeviceDetailDrawer() {
  const { selectedDevice, screenshotData, deviceApps, loadingScreenshot, loadingApps, drawerOpen, closeDrawer, connectDevice, disconnectDevice, enableWireless, enablingWireless } = useDeviceStore();

  if (!drawerOpen || !selectedDevice) return null;

  const device = selectedDevice;

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'android': return <div className="w-3 h-3 rounded-full bg-[#3ddc84]" />;
      case 'ios': return <div className="w-3 h-3 rounded-full bg-white" />;
      case 'harmonyos': return <div className="w-3 h-3 rounded-full bg-[#007dff]" />;
      default: return null;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'connected': return <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full">在线</span>;
      case 'disconnected': return <span className="px-2 py-1 bg-gray-500/20 text-gray-400 text-xs rounded-full">离线</span>;
      case 'busy': return <span className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">忙碌</span>;
      default: return null;
    }
  };

  const infoItems = [
    { label: '型号', value: device.model },
    { label: '制造商', value: device.manufacturer },
    { label: '系统版本', value: device.os_version },
    { label: '分辨率', value: device.screen_width && device.screen_height ? `${device.screen_width}×${device.screen_height}` : undefined },
    { label: '连接类型', value: device.connection_type === 'usb' ? 'USB' : device.connection_type === 'tcpip' ? '无线' : undefined },
    { label: 'IP地址', value: device.ip },
    { label: '电池电量', value: device.battery_level ? `${device.battery_level}%` : undefined },
    { label: '最后在线', value: device.last_seen },
  ];

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDrawer();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [closeDrawer]);

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={closeDrawer} />
      <div className="fixed right-0 top-0 h-full w-[400px] bg-[#1e293b] border-l border-[#334155] z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#334155]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#0f172a] rounded-xl flex items-center justify-center">
              <Smartphone className="w-5 h-5 text-[#64748b]" />
            </div>
            <div>
              <h3 className="text-white font-medium">{device.name}</h3>
              <div className="flex items-center gap-2 mt-1">
                {getPlatformIcon(device.platform)}
                <span className="text-[#94a3b8] text-sm capitalize">{device.platform}</span>
                {getStatusBadge(device.status)}
              </div>
            </div>
          </div>
          <button onClick={closeDrawer} className="p-2 text-[#64748b] hover:text-white rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Device info */}
        <div className="p-4 border-b border-[#334155]">
          <h4 className="text-[#94a3b8] text-sm font-medium mb-3">设备信息</h4>
          <div className="space-y-2">
            {infoItems.filter(item => item.value).map(item => (
              <div key={item.label} className="flex justify-between text-sm">
                <span className="text-[#64748b]">{item.label}</span>
                <span className="text-[#94a3b8]">{item.value}</span>
              </div>
            ))}
            <div className="flex justify-between text-sm">
              <span className="text-[#64748b]">设备ID</span>
              <span className="text-[#94a3b8] font-mono text-xs">{device.device_id}</span>
            </div>
          </div>
        </div>

        {/* Screenshot */}
        <div className="p-4 border-b border-[#334155]">
          <h4 className="text-[#94a3b8] text-sm font-medium mb-3">实时截图</h4>
          {loadingScreenshot ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            </div>
          ) : screenshotData ? (
            <div className="relative">
              <img src={`data:image/png;base64,${screenshotData}`} alt="Device screenshot" className="w-full rounded-lg border border-[#334155]" />
              <button
                onClick={() => useDeviceStore.getState().openDrawer(device)}
                className="absolute top-2 right-2 p-1.5 bg-[#0f172a]/80 hover:bg-[#0f172a] text-white rounded-lg transition-colors"
                title="刷新截图"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 bg-[#0f172a] rounded-lg border border-[#334155]">
              <div className="text-center">
                <AlertCircle className="w-8 h-8 text-[#475569] mx-auto mb-2" />
                <p className="text-[#64748b] text-sm">截图获取失败</p>
              </div>
            </div>
          )}
        </div>

        {/* Installed apps */}
        <div className="p-4 flex-1 overflow-y-auto">
          <h4 className="text-[#94a3b8] text-sm font-medium mb-3">已安装应用</h4>
          {loadingApps ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
            </div>
          ) : deviceApps.length > 0 ? (
            <div className="space-y-1">
              {deviceApps.map(app => (
                <div key={app.package_name} className="flex justify-between text-sm py-1.5 px-2 rounded hover:bg-[#0f172a]/50">
                  <span className="text-[#94a3b8]">{app.name}</span>
                  <span className="text-[#64748b] font-mono text-xs">{app.package_name}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[#64748b] text-sm text-center py-4">暂无数据</p>
          )}
        </div>

        {/* Action buttons */}
        <div className="p-4 border-t border-[#334155] flex gap-2">
          {device.status === 'disconnected' ? (
            <button
              onClick={() => connectDevice(device.device_id)}
              className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
            >
              <Power className="w-4 h-4" />
              连接
            </button>
          ) : (
            <>
              {device.connection_type === 'usb' && (
                <button
                  onClick={() => enableWireless(device.device_id)}
                  disabled={enablingWireless}
                  className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Wifi className="w-4 h-4" />
                  {enablingWireless ? '开启中...' : '开启无线'}
                </button>
              )}
              <button
                onClick={() => disconnectDevice(device.device_id)}
                className="flex-1 py-2 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Power className="w-4 h-4" />
                断开
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 3: Add slide-in animation to global CSS**

Find the global CSS file (check `frontend/src/index.css`). Add the animation:

```css
@keyframes slide-in-right {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
.animate-slide-in-right {
  animation: slide-in-right 0.3s ease-out;
}
```

- [ ] **Step 4: Wire up the detail button in DevicePage**

Open `frontend/src/pages/Device/DevicePage.tsx`.

Add the import:
```tsx
import { DeviceDetailDrawer } from '../../components/DeviceDetailDrawer';
```

Add `openDrawer` to the store destructuring:
```tsx
  const { devices, fetchDevices, connectDevice, disconnectDevice, enableWireless, enablingWireless, openDrawer, error, success, clearMessages } = useDeviceStore();
```

Replace the dead "详情" button onClick:
```tsx
              <button
                onClick={() => openDrawer(device)}
                className="flex-1 py-2 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                <Monitor className="w-4 h-4" />
                详情
              </button>
```

Add `<DeviceDetailDrawer />` at the end of the component JSX, after the empty state section and before the closing `</div>`:
```tsx
      <DeviceDetailDrawer />
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DeviceDetailDrawer.tsx frontend/src/stores/deviceStore.ts frontend/src/pages/Device/DevicePage.tsx frontend/src/index.css
git commit -m "feat: add device detail drawer with screenshot, apps, and actions"
```

---

### Task 4: Report Batch Delete

**Files:**
- Modify: `backend/app/schemas/report.py`
- Modify: `backend/app/services/report_service.py`
- Modify: `backend/app/api/v1/reports.py`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/stores/reportStore.ts`
- Modify: `frontend/src/pages/Report/ReportPage.tsx`

- [ ] **Step 1: Add batch delete schemas**

Open `backend/app/schemas/report.py`. Add at the end:

```python
class BatchDeleteRequest(BaseModel):
    """Request model for batch deleting reports."""
    report_ids: List[str]


class BatchDeleteResponse(BaseModel):
    """Response model for batch deleting reports."""
    deleted_count: int
    failed_ids: List[str] = []
```

- [ ] **Step 2: Add batch_delete method to ReportService**

Open `backend/app/services/report_service.py`. Add the method at the end:

```python
    def batch_delete(self, report_ids: list[str]) -> tuple[int, list[str]]:
        """Batch delete reports. Returns (deleted_count, failed_ids)."""
        deleted = 0
        failed = []
        for report_id in report_ids:
            if report_id in self.reports:
                del self.reports[report_id]
                deleted += 1
            else:
                failed.append(report_id)
        return deleted, failed
```

- [ ] **Step 3: Add batch delete API endpoint**

Open `backend/app/api/v1/reports.py`. Update the imports:
```python
from app.schemas.report import ReportInfo, ReportStatus, ReportType, BatchDeleteRequest, BatchDeleteResponse
```

**CRITICAL: Place this BEFORE `@router.delete("/{report_id}")` to avoid path conflicts.** Add after `list_reports`:

```python
@router.delete("/batch", response_model=BatchDeleteResponse)
async def batch_delete_reports(request: BatchDeleteRequest):
    """Batch delete multiple reports."""
    deleted, failed = report_service.batch_delete(request.report_ids)
    return BatchDeleteResponse(deleted_count=deleted, failed_ids=failed)
```

- [ ] **Step 4: Add frontend API method**

Open `frontend/src/services/api.ts`. Add `batchDeleteReports` to the `reportApi` object:

```typescript
  batchDeleteReports: (reportIds: string[]) =>
    api.delete('/api/v1/reports/batch', { data: { report_ids: reportIds } }),
```

- [ ] **Step 5: Add store action**

Open `frontend/src/stores/reportStore.ts`. Add to the `ReportState` interface:
```typescript
  batchDeleteReports: (reportIds: string[]) => Promise<void>;
```

Add the action implementation:
```typescript
  batchDeleteReports: async (reportIds: string[]) => {
    try {
      await reportApi.batchDeleteReports(reportIds);
      await get().fetchReports();
    } catch (error) {
      set({ error: 'Failed to batch delete reports' });
    }
  },
```

- [ ] **Step 6: Update ReportPage with checkbox and batch action bar**

Open `frontend/src/pages/Report/ReportPage.tsx`. 

Add imports:
```tsx
import { useState } from 'react';
import { FileText, Download, Trash2, Clock, CheckCircle2, XCircle, Loader2, Calendar, CheckSquare, Square, X } from 'lucide-react';
```

Add `batchDeleteReports` to store destructuring:
```tsx
  const { reports, fetchReports, deleteReport, downloadReport, batchDeleteReports } = useReportStore();
```

Add state:
```tsx
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
```

Add toggle helpers:
```tsx
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === reports.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(reports.map(r => r.report_id)));
    }
  };

  const handleBatchDelete = async () => {
    if (!confirm(`确定要删除 ${selectedIds.size} 个报告吗？`)) return;
    await batchDeleteReports(Array.from(selectedIds));
    setSelectedIds(new Set());
  };
```

Add batch action bar before the report table:
```tsx
      {selectedIds.size > 0 && (
        <div className="mb-4 p-3 bg-indigo-900/30 border border-indigo-500/30 rounded-lg flex items-center justify-between">
          <span className="text-indigo-300 font-medium">已选择 {selectedIds.size} 项</span>
          <div className="flex gap-2">
            <button
              onClick={handleBatchDelete}
              className="px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              批量删除
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              className="px-4 py-1.5 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <X className="w-4 h-4" />
              取消选择
            </button>
          </div>
        </div>
      )}
```

Add checkbox header column (before "报告名称"):
```tsx
<th className="text-left py-4 px-4 font-medium w-10">
  <button onClick={toggleSelectAll} className="text-[#94a3b8] hover:text-white transition-colors">
    {selectedIds.size === reports.length && reports.length > 0 ? (
      <CheckSquare className="w-4 h-4" />
    ) : (
      <Square className="w-4 h-4" />
    )}
  </button>
</th>
```

Add checkbox cell in each row (before "报告名称"):
```tsx
<td className="py-4 px-4">
  <button onClick={() => toggleSelect(report.report_id)} className="text-[#94a3b8] hover:text-white transition-colors">
    {selectedIds.has(report.report_id) ? (
      <CheckSquare className="w-4 h-4 text-indigo-400" />
    ) : (
      <Square className="w-4 h-4" />
    )}
  </button>
</td>
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/report.py backend/app/services/report_service.py backend/app/api/v1/reports.py frontend/src/services/api.ts frontend/src/stores/reportStore.ts frontend/src/pages/Report/ReportPage.tsx
git commit -m "feat: add report batch delete with checkboxes and action bar"
```

---

### Task 5: Log Search, Preview, and Pagination

**Files:**
- Modify: `frontend/src/pages/Logs/LogsPage.tsx`

- [ ] **Step 1: Rewrite LogsPage with server-side search, pagination, and detail display**

Open `frontend/src/pages/Logs/LogsPage.tsx`. Replace the entire file content:

```tsx
import { useEffect, useState, useCallback } from 'react';
import { FileText, Search, Filter, RefreshCw, Trash2, AlertCircle, AlertTriangle, Info, Bug, Clock, ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from 'lucide-react';
import { logApi } from '../../services/api';

interface LogEntry {
  log_id: string;
  level: 'debug' | 'info' | 'warning' | 'error';
  category: 'device' | 'script' | 'task' | 'agent' | 'system' | 'api';
  action: string;
  operator: 'user' | 'system' | 'agent';
  target_id?: string;
  target_name?: string;
  detail?: Record<string, unknown>;
  device_id?: string;
  script_id?: string;
  task_id?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  duration_ms?: number;
  error?: string;
  created_at: string;
}

interface LogSummary {
  total: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  debug_count: number;
  avg_response_time_ms?: number;
}

const PAGE_SIZE = 50;

export function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [summary, setSummary] = useState<LogSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedLog, setExpandedLog] = useState<string | null>(null);
  const [totalLogs, setTotalLogs] = useState(0);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const fetchSummary = useCallback(async () => {
    try {
      const response = await logApi.getSummary() as unknown as LogSummary;
      setSummary(response);
      setTotalLogs(response.total);
    } catch (error) {
      console.error('Failed to fetch log summary:', error);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const skip = (currentPage - 1) * PAGE_SIZE;
      const params: Record<string, any> = { skip, limit: PAGE_SIZE };
      if (debouncedSearch) params.search = debouncedSearch;
      if (selectedLevel !== 'all') params.level = selectedLevel;
      if (selectedCategory !== 'all') params.category = selectedCategory;
      if (startTime) params.start_time = startTime;
      if (endTime) params.end_time = endTime;

      const response = await logApi.getLogs(params) as unknown as LogEntry[];
      setLogs(response);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  }, [currentPage, debouncedSearch, selectedLevel, selectedCategory, startTime, endTime]);

  // Fetch summary on mount
  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  // Re-fetch logs when filters change
  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  // Reset to page 1 when filters change
  useEffect(() => { setCurrentPage(1); }, [debouncedSearch, selectedLevel, selectedCategory, startTime, endTime]);

  const handleClearLogs = async () => {
    if (!confirm('确定要清空所有日志吗？')) return;
    try {
      await logApi.clearLogs();
      setLogs([]);
      setSummary(null);
      setCurrentPage(1);
      fetchSummary();
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  };

  const totalPages = Math.ceil(totalLogs / PAGE_SIZE);

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error': return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'info': return <Info className="w-4 h-4 text-blue-400" />;
      case 'debug': return <Bug className="w-4 h-4 text-purple-400" />;
      default: return <Info className="w-4 h-4 text-gray-400" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'bg-red-500/20 text-red-400';
      case 'warning': return 'bg-yellow-500/20 text-yellow-400';
      case 'info': return 'bg-blue-500/20 text-blue-400';
      case 'debug': return 'bg-purple-500/20 text-purple-400';
      default: return 'bg-gray-500/20 text-gray-400';
    }
  };

  const getCategoryLabel = (category: string) => {
    const map: Record<string, string> = { device: '设备操作', script: '脚本操作', task: '任务操作', agent: 'Agent操作', system: '系统', api: 'API请求' };
    return map[category] || category;
  };

  const formatTime = (ts: string) => new Date(ts).toLocaleString('zh-CN');

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-400" />
            日志管理
          </h1>
          <p className="text-[#94a3b8] mt-1">查看和管理系统日志记录</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => { fetchSummary(); fetchLogs(); }} className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors">
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
          <button onClick={handleClearLogs} className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg flex items-center gap-2 transition-colors">
            <Trash2 className="w-4 h-4" />
            清空日志
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center"><FileText className="w-5 h-5 text-blue-400" /></div>
              <div><p className="text-[#64748b] text-sm">总日志数</p><p className="text-white text-xl font-bold">{summary.total}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center"><AlertCircle className="w-5 h-5 text-red-400" /></div>
              <div><p className="text-[#64748b] text-sm">错误</p><p className="text-white text-xl font-bold">{summary.error_count}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center"><AlertTriangle className="w-5 h-5 text-yellow-400" /></div>
              <div><p className="text-[#64748b] text-sm">警告</p><p className="text-white text-xl font-bold">{summary.warning_count}</p></div>
            </div>
          </div>
          <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center"><Clock className="w-5 h-5 text-green-400" /></div>
              <div><p className="text-[#64748b] text-sm">平均响应时间</p><p className="text-white text-xl font-bold">{summary.avg_response_time_ms?.toFixed(1) || '-'}ms</p></div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-4 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-[#94a3b8]" />
          <span className="text-[#94a3b8] text-sm">筛选条件</span>
        </div>
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-[#94a3b8] text-sm mb-2">搜索日志</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
              <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 pl-10 pr-4 text-white placeholder-[#64748b] focus:outline-none focus:border-indigo-500" placeholder="搜索日志内容..." />
            </div>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">日志级别</label>
            <select value={selectedLevel} onChange={(e) => setSelectedLevel(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500">
              <option value="all">全部</option><option value="error">错误</option><option value="warning">警告</option><option value="info">信息</option><option value="debug">调试</option>
            </select>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">日志类别</label>
            <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500">
              <option value="all">全部</option><option value="device">设备操作</option><option value="script">脚本操作</option><option value="task">任务操作</option><option value="agent">Agent操作</option><option value="system">系统</option><option value="api">API请求</option>
            </select>
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">开始时间</label>
            <input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-3 text-white focus:outline-none focus:border-indigo-500" />
          </div>
          <div>
            <label className="block text-[#94a3b8] text-sm mb-2">结束时间</label>
            <input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} className="bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-3 text-white focus:outline-none focus:border-indigo-500" />
          </div>
        </div>
      </div>

      {/* Log List */}
      {loading ? (
        <div className="text-center py-20">
          <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-[#94a3b8]">加载中...</p>
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-20">
          <FileText className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无日志</h3>
          <p className="text-[#64748b]">没有符合条件的日志记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <div key={log.log_id} className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
              <div className="p-4 cursor-pointer hover:bg-[#0f172a]/50 transition-colors" onClick={() => setExpandedLog(expandedLog === log.log_id ? null : log.log_id)}>
                <div className="flex items-start gap-4">
                  <div className="mt-1">{getLevelIcon(log.level)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getLevelColor(log.level)}`}>{log.level.toUpperCase()}</span>
                      <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">{getCategoryLabel(log.category)}</span>
                      <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded text-xs">{log.action}</span>
                      {log.status_code && <span className={`px-2 py-0.5 rounded text-xs font-medium ${log.status_code >= 400 ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>{log.status_code}</span>}
                      {log.duration_ms && <span className="px-2 py-0.5 bg-[#334155] text-[#94a3b8] rounded text-xs">{log.duration_ms}ms</span>}
                    </div>
                    <p className="text-white mt-2 line-clamp-2">{log.action}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-[#64748b]">
                      <span>{formatTime(log.created_at)}</span>
                      {log.target_name && <span>目标: {log.target_name}</span>}
                      {log.device_id && <span>设备: {log.device_id}</span>}
                      {log.endpoint && <span>端点: {log.endpoint}</span>}
                    </div>
                  </div>
                  <button className="text-[#64748b] hover:text-white transition-colors">
                    {expandedLog === log.log_id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {expandedLog === log.log_id && (
                <div className="border-t border-[#334155] bg-[#0f172a]/30 p-4">
                  <div className="space-y-3">
                    {log.error && (<div><p className="text-[#94a3b8] text-sm mb-1">错误信息</p><p className="text-red-400 text-sm font-mono">{log.error}</p></div>)}
                    {log.target_name && (<div><p className="text-[#94a3b8] text-sm mb-1">目标名称</p><p className="text-white text-sm">{log.target_name}</p></div>)}
                    {log.target_id && (<div><p className="text-[#94a3b8] text-sm mb-1">目标ID</p><p className="text-white text-sm font-mono">{log.target_id}</p></div>)}
                    {log.endpoint && (<div><p className="text-[#94a3b8] text-sm mb-1">请求端点</p><p className="text-white text-sm font-mono">{log.method} {log.endpoint}</p></div>)}
                    {log.detail && Object.keys(log.detail).length > 0 && (
                      <div>
                        <p className="text-[#94a3b8] text-sm mb-1">详细信息</p>
                        <pre className="text-[#94a3b8] text-sm font-mono bg-[#0f172a] rounded-lg p-3 overflow-auto max-h-48">{JSON.stringify(log.detail, null, 2)}</pre>
                      </div>
                    )}
                    <div><p className="text-[#94a3b8] text-sm mb-1">日志ID</p><p className="text-white text-sm font-mono">{log.log_id}</p></div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6 px-4">
          <p className="text-[#94a3b8] text-sm">第 {currentPage} 页 / 共 {totalPages} 页 ({totalLogs} 条日志)</p>
          <div className="flex gap-2">
            <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="px-3 py-1.5 bg-[#334155] hover:bg-[#475569] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-1 transition-colors">
              <ChevronLeft className="w-4 h-4" />上一页
            </button>
            <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="px-3 py-1.5 bg-[#334155] hover:bg-[#475569] disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-1 transition-colors">
              下一页<ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Logs/LogsPage.tsx
git commit -m "feat: rewrite log page with server-side search, pagination, detail display, and time filters"
```

---

## Self-Review

1. **Spec coverage**: All 5 issues mapped to tasks ✅
2. **Placeholder scan**: No TBD/TODO/placeholder patterns found ✅
3. **Type consistency**: All types, method signatures, and field names are consistent across tasks ✅