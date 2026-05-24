# Platform Bugfixes & Enhancements Design

**Date:** 2026-05-22
**Status:** Approved
**Approach:** Minimal fix (方案A)

---

## Overview

5 bug fixes / UX enhancements for the device management, APK management, and task management modules. All changes are small, targeted fixes to existing code — no new tools, no architecture changes.

## Change Summary

| # | Module | Issue | Fix |
|---|--------|-------|-----|
| 1 | APK管理 | 列结构 | No change needed — current 6 columns match requirements |
| 2 | 设备管理 | WiFi开启逻辑 | Check `connection_type` before enabling wireless; if already tcpip, show "已连接" message |
| 3 | 设备详情 | 已安装应用 + 电量 | Remove installed apps section; fix `battery_level` field missing in `DeviceInfo` construction |
| 4 | 设备信息 | 型号/类型/版本号 | Card shows model + os_version; drawer shows full info including `device_type` and `android_sdk_version`; backend passes all fields |
| 5 | 任务管理 | 设备选择 | Only show online devices; label each as WiFi在线 or USB在线 |

---

## 1. APK管理 — No Change

Current columns (APK文件名, 包名, 版本号, 大小, 上传时间, 操作) already match requirements. `apk_service.py` uses aapt2 for package name parsing with aapt fallback. No modifications needed.

---

## 2. 设备管理 — WiFi开启逻辑优化

### Problem
Clicking "开启无线" always runs the full `enable_wireless_connection` flow (get IP → tcpip mode → connect), even if the device is already connected via WiFi (`connection_type === 'tcpip'`). This causes redundant operations and potential connection disruption.

### Fix

**Frontend (`deviceStore.ts`):**
- In `enableWireless` method, before calling the API:
  - Check device's `connection_type` from the current devices list
  - If `connection_type === 'tcpip'`: set `success` message "该设备已通过WiFi连接" and return early, no API call
  - If `connection_type === 'usb'`: proceed with normal `enableWireless` API call

**Frontend (`DeviceDetailDrawer.tsx` & `DevicePage.tsx`):**
- For devices with `connection_type === 'tcpip'`: keep "开启无线" button visible but when clicked, show "已连接" toast instead of executing the flow
- The button text stays "开启无线" — the feedback happens on click

---

## 3. 设备详情 — 去掉已安装应用 + 修复电量

### Problem 1: Installed apps section unnecessary
The "已安装应用" section in `DeviceDetailDrawer` is not needed per requirements.

### Fix 1
- **`DeviceDetailDrawer.tsx`**: Delete the entire "已安装应用" section (HTML block + loading state)
- **`deviceStore.ts`**: Remove `deviceApps`, `loadingApps` fields and related logic from the store interface and `openDrawer` method
- **`openDrawer`**: No longer call `/api/v1/devices/{id}/apps` endpoint
- Backend `get_installed_apps` method remains (may be used elsewhere) — only frontend stops calling it

### Problem 2: Battery level not displayed
Backend `_get_device_info` correctly extracts `battery_level` from `adb shell dumpsys battery`, but `list_devices` does not pass it to the `DeviceInfo` constructor.

### Fix 2
- **`device_service.py`**: Add `battery_level=device.get("battery_level")`, `device_type=device.get("device_type")`, `android_sdk_version=device.get("android_sdk_version")` to the `DeviceInfo` construction in `list_devices`
- Battery display: `{battery_level}%` format — percentage only, no additional info needed

---

## 4. 设备信息显示 — 卡片简化 + 抽屉完整

### Problem
- Device card shows `model` and `os_version` but could be more informative
- Detail drawer lacks `device_type` and `android_sdk_version`
- Backend `DeviceInfo` construction omits `battery_level`, `device_type`, `android_sdk_version`

### Fix

**Backend (`device_service.py`):**
- In `list_devices` → `DeviceInfo` construction, add:
  - `battery_level=device.get("battery_level")`
  - `device_type=device.get("device_type")`
  - `android_sdk_version=device.get("android_sdk_version")`

**Frontend `Device` interface (`deviceStore.ts`):**
- Add `device_type?: string` and `android_sdk_version?: string` to the Device interface

**Device Card (`DevicePage.tsx`):**
- Current display: model, os_version, connection type, status — keep as-is (simplified view)

**Detail Drawer (`DeviceDetailDrawer.tsx`):**
- Add display for `device_type` (设备类型) and `android_sdk_version` (SDK版本)
- Keep existing: model, manufacturer, os_version, screen resolution, connection_type, ip, battery_level, device_id

---

## 5. 任务管理 — 设备选择仅显示在线 + 标注连接方式

### Problem
Task creation modal shows all devices (online and offline) without distinguishing connection type. Per requirements, only online devices should be selectable, each labeled with its connection method.

### Fix

**`TaskPage.tsx` — Device selection section:**
- Filter: only render devices where `status === 'connected'`
- Label each device with connection type:
  - `connection_type === 'tcpip'` → green badge "WiFi在线"
  - `connection_type === 'usb'` → blue badge "USB在线"
- Remove offline devices from the checkbox list entirely (no grey-out, just don't show)

**`Device` interface:** Already has `connection_type` and `status` fields — no schema changes needed.

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/services/device_service.py` | Add 3 missing fields to `DeviceInfo` construction |
| `frontend/src/stores/deviceStore.ts` | Remove `deviceApps`/`loadingApps`; add `device_type`, `android_sdk_version` to Device interface; add tcpip check in `enableWireless` |
| `frontend/src/pages/Device/DevicePage.tsx` | WiFi button click shows "已连接" for tcpip devices |
| `frontend/src/components/DeviceDetailDrawer.tsx` | Remove installed apps section; add `device_type` and `android_sdk_version` display; WiFi button shows "已连接" for tcpip |
| `frontend/src/pages/Task/TaskPage.tsx` | Filter devices to online only; label WiFi在线/USB在线 |

---

## Out of Scope

- APK管理列结构调整 (no change needed)
- Backend API endpoint changes (no new endpoints)
- New tool integration (aapt2 already used for APK, not needed for device info)
- Device info refactoring / layered fetching architecture