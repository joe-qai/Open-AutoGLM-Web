# Platform Bugfixes & Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 bugs / UX enhancements across device management, device details, and task management modules.

**Architecture:** Minimal patch approach — fix missing field pass-through in backend, add connection_type guard in frontend WiFi logic, remove installed apps section, add device info fields to drawer, and filter task device selection to online-only with connection labels.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript/Zustand (frontend), ADB (device communication)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/app/services/device_service.py` | Modify | Add `battery_level`, `device_type`, `android_sdk_version` to `DeviceInfo` construction in `list_devices` |
| `frontend/src/stores/deviceStore.ts` | Modify | Remove `deviceApps`/`loadingApps`; add `device_type`/`android_sdk_version` to Device interface; add tcpip check in `enableWireless` |
| `frontend/src/pages/Device/DevicePage.tsx` | Modify | WiFi button for tcpip devices shows "已连接" toast on click |
| `frontend/src/components/DeviceDetailDrawer.tsx` | Modify | Remove installed apps section; add `device_type`/`android_sdk_version` display; WiFi button tcpip guard |
| `frontend/src/pages/Task/TaskPage.tsx` | Modify | Filter devices to online-only; add WiFi在线/USB在线 badges |

---

### Task 1: Backend — Fix missing DeviceInfo fields

**Files:**
- Modify: `backend/app/services/device_service.py:237-249`

- [ ] **Step 1: Add missing fields to DeviceInfo construction in `list_devices`**

In `device_service.py`, the `DeviceInfo` construction at line 237 is missing `battery_level`, `device_type`, and `android_sdk_version`. These are already extracted by `_get_device_info` but never passed through. Add them:

```python
            device_list.append(DeviceInfo(
                device_id=device["device_id"],
                name=device["name"],
                platform=PlatformType(device["platform"]),
                status=DeviceStatus(device["status"]),
                connection_type=ConnectionType(device["connection_type"]),
                ip=device["ip"],
                model=device["model"],
                manufacturer=device["manufacturer"],
                os_version=device["os_version"],
                screen_width=device["screen_width"],
                screen_height=device["screen_height"],
                battery_level=device.get("battery_level"),
                device_type=device.get("device_type"),
                android_sdk_version=device.get("android_sdk_version")
            ))
```

- [ ] **Step 2: Verify backend starts without errors**

Run: `cd backend && python -c "from app.services.device_service import DeviceService; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/device_service.py
git commit -m "fix: pass battery_level, device_type, android_sdk_version through DeviceInfo"
```

---

### Task 2: Frontend Store — Remove apps, add fields, add WiFi guard

**Files:**
- Modify: `frontend/src/stores/deviceStore.ts`

- [ ] **Step 1: Remove `deviceApps` and `loadingApps` from the store**

In `deviceStore.ts`, delete these from the `DeviceState` interface:

Remove from interface:
```typescript
  deviceApps: { package_name: string; name: string }[];
  loadingApps: boolean;
```

Remove from initial state:
```typescript
  deviceApps: [],
  loadingApps: false,
```

- [ ] **Step 2: Add `device_type` and `android_sdk_version` to Device interface**

In `deviceStore.ts`, add to the `Device` interface after `battery_level?: number;`:

```typescript
  device_type?: string;
  android_sdk_version?: string;
```

- [ ] **Step 3: Simplify `openDrawer` — remove apps API call**

Replace the current `openDrawer` method. Remove the apps-fetching block and `deviceApps`/`loadingApps` from the `set()` calls:

Current `openDrawer`:
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
```

New `openDrawer`:
```typescript
  openDrawer: async (device: Device) => {
    set({ selectedDevice: device, drawerOpen: true, screenshotData: null, loadingScreenshot: true });
    try {
      const response = await deviceApi.getScreenshot(device.device_id) as unknown as { screenshot_base64: string };
      set({ screenshotData: response.screenshot_base64, loadingScreenshot: false });
    } catch {
      set({ screenshotData: null, loadingScreenshot: false });
    }
  },
```

- [ ] **Step 4: Simplify `closeDrawer` — remove apps cleanup**

Current `closeDrawer`:
```typescript
  closeDrawer: () => {
    set({ drawerOpen: false, screenshotData: null, deviceApps: [] });
  },
```

New `closeDrawer`:
```typescript
  closeDrawer: () => {
    set({ drawerOpen: false, screenshotData: null });
  },
```

- [ ] **Step 5: Add tcpip check in `enableWireless`**

Add a guard at the start that checks if the device is already on tcpip and returns early with a success message:

Current `enableWireless`:
```typescript
  enableWireless: async (deviceId: string, port: number = 5555) => {
    set({ enablingWirelessDeviceId: deviceId, error: null, success: null });
    try {
      const response = await deviceApi.enableWireless(deviceId, port) as unknown as {
        success: boolean;
        message: string;
        device_id?: string;
      };

      if (response.success) {
        await get().fetchDevices();
        set({ enablingWirelessDeviceId: null, success: response.message });
      } else {
        set({ enablingWirelessDeviceId: null, error: response.message });
      }
    } catch (error: any) {
      set({
        enablingWirelessDeviceId: null,
        error: error.response?.data?.detail || 'Failed to enable wireless connection'
      });
    }
  },
```

New `enableWireless`:
```typescript
  enableWireless: async (deviceId: string, port: number = 5555) => {
    const device = get().devices.find(d => d.device_id === deviceId);
    if (device && device.connection_type === 'tcpip') {
      set({ success: '该设备已通过WiFi连接' });
      return;
    }
    set({ enablingWirelessDeviceId: deviceId, error: null, success: null });
    try {
      const response = await deviceApi.enableWireless(deviceId, port) as unknown as {
        success: boolean;
        message: string;
        device_id?: string;
      };

      if (response.success) {
        await get().fetchDevices();
        set({ enablingWirelessDeviceId: null, success: response.message });
      } else {
        set({ enablingWirelessDeviceId: null, error: response.message });
      }
    } catch (error: any) {
      set({
        enablingWirelessDeviceId: null,
        error: error.response?.data?.detail || 'Failed to enable wireless connection'
      });
    }
  },
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/stores/deviceStore.ts
git commit -m "fix: remove apps state, add device_type/android_sdk_version, guard enableWireless for tcpip"
```

---

### Task 3: DeviceDetailDrawer — Remove apps, add fields, WiFi button guard

**Files:**
- Modify: `frontend/src/components/DeviceDetailDrawer.tsx`

- [ ] **Step 1: Remove `deviceApps` and `loadingApps` from destructuring**

Current destructuring:
```typescript
  const { selectedDevice, drawerOpen, screenshotData, deviceApps, loadingScreenshot, loadingApps, closeDrawer, connectDevice, disconnectDevice, enableWireless, enablingWirelessDeviceId } = useDeviceStore();
```

New destructuring:
```typescript
  const { selectedDevice, drawerOpen, screenshotData, loadingScreenshot, closeDrawer, connectDevice, disconnectDevice, enableWireless, enablingWirelessDeviceId } = useDeviceStore();
```

- [ ] **Step 2: Delete the entire "已安装应用" section**

Remove the block from line 170 to line 191 — the `{/* Installed Apps Section */}` div containing the apps list and loading state. Delete all of it.

- [ ] **Step 3: Add `device_type` and `android_sdk_version` display to the info section**

After the `{selectedDevice.os_version && (...)}` block (around line 95-100), add these two new info rows:

```tsx
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
```

- [ ] **Step 4: Remove `connection_type === 'usb'` condition from WiFi button in drawer**

At lines 207-214, the WiFi button only shows for USB devices. Per spec, it should show for all connected devices (tcpip click gives "已连接" feedback via the store guard):

Current:
```tsx
                {selectedDevice.connection_type === 'usb' && (
                  <button
                    onClick={() => enableWireless(selectedDevice.device_id)}
                    disabled={enablingWirelessDeviceId === selectedDevice.device_id}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Wifi className="w-4 h-4" />
                    {enablingWirelessDeviceId === selectedDevice.device_id ? '开启中...' : '开启无线'}
                  </button>
                )}
```

New — remove the wrapping condition:
```tsx
                  <button
                    onClick={() => enableWireless(selectedDevice.device_id)}
                    disabled={enablingWirelessDeviceId === selectedDevice.device_id}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Wifi className="w-4 h-4" />
                    {enablingWirelessDeviceId === selectedDevice.device_id ? '开启中...' : '开启无线'}
                  </button>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DeviceDetailDrawer.tsx
git commit -m "fix: remove installed apps section, add device_type/sdk_version, show WiFi button for all connected devices"
```

---

### Task 4: DevicePage — WiFi button tcpip guard

**Files:**
- Modify: `frontend/src/pages/Device/DevicePage.tsx`

- [ ] **Step 1: Remove `connection_type === 'usb'` condition from WiFi button**

At lines 188-196, the WiFi button only shows for USB devices. Per spec, it should show for all connected devices. The store's `enableWireless` already has the tcpip guard (Task 2), so clicking on a tcpip device will show "已连接" message.

Current (lines 188-196):
```tsx
                  {device.connection_type === 'usb' && (
                    <button
                      onClick={() => enableWireless(device.device_id)}
                      disabled={enablingWirelessDeviceId === device.device_id}
                      className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Wifi className="w-4 h-4" />
                      {enablingWirelessDeviceId === device.device_id ? '开启中...' : '开启无线'}
                    </button>
                  )}
```

New — remove the wrapping condition:
```tsx
                  <button
                    onClick={() => enableWireless(device.device_id)}
                    disabled={enablingWirelessDeviceId === device.device_id}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm rounded-lg flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Wifi className="w-4 h-4" />
                    {enablingWirelessDeviceId === device.device_id ? '开启中...' : '开启无线'}
                  </button>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Device/DevicePage.tsx
git commit -m "fix: show WiFi button for all connected devices, tcpip click shows '已连接'"
```

---

### Task 5: TaskPage — Online-only device filter + connection badges

**Files:**
- Modify: `frontend/src/pages/Task/TaskPage.tsx`

- [ ] **Step 1: Filter devices to online-only and add connection badges**

In the device selection section (lines 340-363), replace the current device list rendering with a filtered version that:
1. Only shows devices with `status === 'connected'`
2. Shows green "WiFi在线" badge for tcpip devices and blue "USB在线" badge for usb devices

Current device checkbox section (lines 340-363):
```tsx
                  {devices.map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedDeviceIds.includes(device.device_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDeviceIds([...selectedDeviceIds, device.device_id]);
                          } else {
                            setSelectedDeviceIds(selectedDeviceIds.filter(id => id !== device.device_id));
                          }
                        }}
                        className="w-4 h-4 rounded border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[#94a3b8]">{device.name || device.device_id} ({device.platform})</span>
                      {device.status === 'connected' ? (
                        <span className="text-green-400 text-xs">在线</span>
                      ) : (
                        <span className="text-gray-400 text-xs">离线</span>
                      )}
                    </label>
                  ))}
```

New version:
```tsx
                  {devices.filter(d => d.status === 'connected').map((device) => (
                    <label key={device.device_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedDeviceIds.includes(device.device_id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedDeviceIds([...selectedDeviceIds, device.device_id]);
                          } else {
                            setSelectedDeviceIds(selectedDeviceIds.filter(id => id !== device.device_id));
                          }
                        }}
                        className="w-4 h-4 rounded border-[#334155] bg-[#0f172a] text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[#94a3b8]">{device.name || device.device_id} ({device.platform})</span>
                      {device.connection_type === 'tcpip' ? (
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">WiFi在线</span>
                      ) : (
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 text-xs rounded-full">USB在线</span>
                      )}
                    </label>
                  ))}
                  {devices.filter(d => d.status === 'connected').length === 0 && (
                    <p className="text-[#64748b] text-sm">暂无在线设备</p>
                  )}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Task/TaskPage.tsx
git commit -m "fix: filter task device selection to online-only, add WiFi/USB在线 badges"
```

---

## Self-Review

### Spec Coverage

| Spec Item | Plan Task |
|-----------|-----------|
| 1. APK管理 no change | No task needed — confirmed no change |
| 2. WiFi开启逻辑 — tcpip guard in store | Task 2 Step 5 (store guard) + Task 4 Step 1 (DevicePage button) + Task 3 Step 4 (Drawer button) |
| 3a. Remove installed apps section | Task 2 Steps 1-4 (store) + Task 3 Steps 1-2 (drawer) |
| 3b. Fix battery_level field | Task 1 Step 1 (backend) |
| 4. Device info — device_type, android_sdk_version | Task 1 Step 1 (backend) + Task 2 Step 2 (interface) + Task 3 Step 3 (drawer display) |
| 5. Task device selection filter + badges | Task 5 Step 1 |

All spec items covered. No gaps.

### Placeholder Scan

No TBD, TODO, or "implement later" patterns found. All steps contain complete code.

### Type Consistency

- `Device.device_type?: string` defined in Task 2 Step 2, used in Task 3 Step 3 — matches
- `Device.android_sdk_version?: string` defined in Task 2 Step 2, used in Task 3 Step 3 — matches
- `connection_type === 'tcpip'` check used consistently in Task 2 Step 5, Task 4 Step 1, Task 5 Step 1, Task 3 Step 4 — matches
- `battery_level=device.get("battery_level")` in Task 1 Step 1 matches `DeviceInfo.battery_level: Optional[int]` in schema — matches