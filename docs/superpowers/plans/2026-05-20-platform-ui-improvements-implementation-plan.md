# Platform UI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对平台前端进行多项UI优化

**Architecture:** Zustand stores, React hooks, Tailwind CSS

**Tech Stack:** React 18, Zustand, Tailwind CSS, TypeScript

---

### Task 1: Dashboard Device Statistics Enhancement

**Files:**
- Modify: `frontend/src/pages/Dashboard/Dashboard.tsx`
- Modify: `frontend/src/stores/deviceStore.ts`

- [ ] **Step 1: Update device statistics logic to group by name**

Edit `frontend/src/stores/deviceStore.ts`:

```typescript
// 按设备名称去重，保留最新状态
export const useDeviceStore = create<DeviceStore>((set, get) => ({
  // ...
  getUniqueDevicesByName: () => {
    const devices = get().devices;
    const uniqueMap = new Map<string, DeviceInfo>();

    devices.forEach((device) => {
      const existing = uniqueMap.get(device.name);
      if (!existing || new Date(device.last_seen) > new Date(existing.last_seen)) {
        uniqueMap.set(device.name, device);
      }
    });

    return Array.from(uniqueMap.values());
  },

  getDevicesByConnectionType: (type: 'usb' | 'wifi') => {
    return get().getUniqueDevicesByName().filter(
      (device) => device.connection_type?.toLowerCase() === type
    );
  }
}));
```

- [ ] **Step 2: Update Dashboard to display USB/WiFi breakdown**

Edit `frontend/src/pages/Dashboard/Dashboard.tsx`:

```typescript
// 添加设备统计组件
const DeviceStats = () => {
  const deviceStore = useDeviceStore();
  const uniqueDevices = deviceStore.getUniqueDevicesByName();
  const usbDevices = deviceStore.getDevicesByConnectionType('usb');
  const wifiDevices = deviceStore.getDevicesByConnectionType('wifi');

  return (
    <div className="grid grid-cols-3 gap-4">
      <StatCard
        icon={<UsbIcon />}
        label="USB"
        count={usbDevices.length}
        color="text-blue-500"
      />
      <StatCard
        icon={<WifiIcon />}
        label="WiFi"
        count={wifiDevices.length}
        color="text-green-500"
      />
      <StatCard
        icon={<DeviceIcon />}
        label="Total"
        count={uniqueDevices.length}
        color="text-gray-500"
      />
    </div>
  );
};

// 设备状态点改进 - 更大带发光效果
const StatusDot = ({ status }: { status: string }) => {
  const isOnline = status === 'online';
  return (
    <span
      className={`
        inline-block w-2.5 h-2.5 rounded-full
        ${isOnline ? 'bg-green-400 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-gray-400'}
      `}
    />
  );
};

// 连接类型 Badge 改进 - 白色粗体
const ConnectionBadge = ({ type }: { type: string }) => {
  const isUsb = type?.toLowerCase() === 'usb';
  return (
    <span className={`text-xs font-bold ${isUsb ? 'text-blue-400' : 'text-green-400'}`}>
      {isUsb ? 'USB' : 'WiFi'}
    </span>
  );
};
```

---

### Task 2: Header Navigation Cleanup

**Files:**
- Modify: `frontend/src/components/layout/Header.tsx`

- [ ] **Step 1: Remove search, notifications, settings icons**

Edit `frontend/src/components/layout/Header.tsx`:

```typescript
// 移除这些导入和使用
// import { SearchIcon, BellIcon, CogIcon } from '@heroicons/react/outline';

// 简化 header 内容
<header className="bg-white shadow-sm border-b border-gray-200">
  <div className="flex items-center justify-between h-16 px-6">
    <div className="flex items-center">
      <h1 className="text-xl font-semibold text-gray-800">
        AutoGLM Platform
      </h1>
    </div>
    {/* 移除了 search, notifications, settings */}
  </div>
</header>
```

---

### Task 3: Script Edit Modal Enhancement

**Files:**
- Modify: `frontend/src/pages/Script/ScriptPage.tsx`

- [ ] **Step 1: Enlarge script edit modal**

Edit `frontend/src/pages/Script/ScriptPage.tsx`:

```typescript
// 查找 Modal 组件的 className
<Dialog
  open={isOpen}
  onClose={onClose}
  className="relative z-50"
>
  <div className="fixed inset-0 bg-black/30" aria-hidden="true" />

  <div className="fixed inset-0 flex items-center justify-center p-4">
    <DialogPanel
      className="
        w-full max-w-5xl
        min-h-[400px]
        bg-white rounded-lg shadow-xl
        p-6
      "
    >
      {/* Script editor content */}
    </DialogPanel>
  </div>
</Dialog>
```

---

### Task 4: Report Batch Delete UI

**Files:**
- Modify: `frontend/src/pages/Report/ReportPage.tsx`
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: Add batch delete API method**

Edit `frontend/src/services/api.ts`:

```typescript
// 添加批量删除方法
batchDeleteReports: async (reportIds: string[]): Promise<void> => {
  await apiRequest('/reports/batch-delete', {
    method: 'POST',
    body: JSON.stringify({ report_ids: reportIds })
  });
}
```

- [ ] **Step 2: Add checkbox column to report table**

Edit `frontend/src/pages/Report/ReportPage.tsx`:

```typescript
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

const toggleSelect = (id: string) => {
  const newSet = new Set(selectedIds);
  if (newSet.has(id)) {
    newSet.delete(id);
  } else {
    newSet.add(id);
  }
  setSelectedIds(newSet);
};

const selectAll = () => {
  if (selectedIds.size === reports.length) {
    setSelectedIds(new Set());
  } else {
    setSelectedIds(new Set(reports.map((r) => r.id)));
  }
};

const handleBatchDelete = async () => {
  if (selectedIds.size === 0) return;
  if (!confirm(`Delete ${selectedIds.size} reports?`)) return;

  try {
    await api.batchDeleteReports(Array.from(selectedIds));
    await refreshReports();
    setSelectedIds(new Set());
  } catch (error) {
    console.error('Batch delete failed:', error);
  }
};

// 添加 Action Bar 当有选中项时显示
{selectedIds.size > 0 && (
  <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white px-6 py-3 rounded-full shadow-lg flex items-center gap-4">
    <span>{selectedIds.size} selected</span>
    <button
      onClick={handleBatchDelete}
      className="px-4 py-1 bg-red-500 hover:bg-red-600 rounded-full"
    >
      Delete
    </button>
    <button
      onClick={() => setSelectedIds(new Set())}
      className="px-4 py-1 bg-gray-600 hover:bg-gray-500 rounded-full"
    >
      Cancel
    </button>
  </div>
)}
```

- [ ] **Step 3: Add checkbox column**

```typescript
// 表头添加全选复选框
<th className="w-12">
  <input
    type="checkbox"
    checked={selectedIds.size === reports.length && reports.length > 0}
    onChange={selectAll}
    className="rounded"
  />
</th>

// 每行添加复选框
<td>
  <input
    type="checkbox"
    checked={selectedIds.has(report.id)}
    onChange={() => toggleSelect(report.id)}
    className="rounded"
  />
</td>
```

---

### Verification

- [ ] Verify dashboard shows USB/WiFi device count breakdown
- [ ] Verify status dots have glow effect for online devices
- [ ] Verify header has no search/notifications/settings icons
- [ ] Verify script edit modal is wider (max-w-5xl) and has min-height
- [ ] Verify report page shows checkboxes and action bar on selection
