# Platform UI Improvements Design

**Date:** 2026-05-20
**Status:** Approved
**Approach:** 平台UI优化

---

## Overview

对平台前端进行多项UI优化：仪表盘设备统计改进、顶部导航栏精简、脚本编辑弹窗放大。

## Change Summary

| # | Module | Issue | Fix |
|---|--------|-------|-----|
| 1 | 仪表盘 | 设备状态文字/圆点与背景撞色 | Text color brighter, dot larger with glow, connection type white+bold |
| 2 | 仪表盘 | 设备按名称聚合，区分连接类型 | 按设备名称去重，USB/WiFi分别显示 |
| 3 | 顶部导航 | 搜索/通知/设置按钮冗余 | Remove search, notifications, settings icons from header |
| 4 | 脚本编辑 | 弹窗太小，无法舒适编辑 | max-w-3xl → max-w-5xl, 添加最小高度 |

---

## 1. Dashboard Device Statistics

### 1.1 Current Issues

- 设备状态圆点颜色与背景对比度不足
- 连接类型（USB/WiFi）显示不清晰
- 同名设备重复显示

### 1.2 Design Changes

**File:** `frontend/src/pages/Dashboard/Dashboard.tsx`

| Element | Before | After |
|---------|--------|-------|
| Status dot | 6px, subtle color | 10px, glow effect |
| Connection badge | 灰色文字 | 白色+粗体 |
| Device list | 按设备ID去重 | 按设备名称去重，分USB/WiFi |

### 1.3 New Layout

```
+------------------------------------------+
|  📊 Dashboard                             |
+------------------------------------------+
|  Device Overview                         |
|  +--------+ +--------+ +--------+        |
|  | ● USB  | | ● WiFi | | Total  |        |
|  |   12   | |    5   | |   17   |        |
|  +--------+ +--------+ +--------+        |
|                                          |
|  Online Devices                          |
|  ┌──────────────────────────────────┐    |
|  │ 设备1  ● USB    85%  Android 14  │    |
|  │ 设备2  ● WiFi   92%  Android 13  │    |
|  │ ...                                │    |
|  └──────────────────────────────────┘    |
+------------------------------------------+
```

---

## 2. Header Navigation Cleanup

### 2.1 Current Layout

```
+----------------------------------------------------------+
| AutoGLM Platform    [Search] [Notifications] [Settings] |
+----------------------------------------------------------+
```

### 2.2 New Layout

```
+----------------------------------------------------------+
| AutoGLM Platform                                         |
+----------------------------------------------------------+
```

**Files:**
- `frontend/src/components/layout/Header.tsx` — 移除 Search、Notifications、Settings 图标

---

## 3. Script Edit Modal Enhancement

### 3.1 Current Issue

- `max-w-3xl` (384px) 宽度不足以舒适编辑代码
- 无最小高度，大脚本显示不完整

### 3.2 Design Changes

**File:** `frontend/src/pages/Script/ScriptPage.tsx`

| Property | Before | After |
|----------|--------|-------|
| max-width | `max-w-3xl` (384px) | `max-w-5xl` (576px) |
| min-height | none | 400px |
| padding | default | p-6 |

---

## 4. Report Batch Delete UI

### 4.1 Current Issue

- 无批量删除功能
- 只能单条删除

### 4.2 Design Changes

**File:** `frontend/src/pages/Report/ReportPage.tsx`

| Feature | Description |
|---------|-------------|
| Checkbox column | 每行左侧添加复选框 |
| Action bar | 选中后显示操作栏（删除按钮） |
| Select all | 表头添加全选复选框 |
| Badge count | 显示选中数量 |

---

## 5. Files to Modify

| File | Changes |
|------|---------|
| `frontend/src/pages/Dashboard/Dashboard.tsx` | 设备统计按名称去重，USB/WiFi分组，状态点样式改进 |
| `frontend/src/components/layout/Header.tsx` | 移除 search/notifications/settings 图标 |
| `frontend/src/pages/Script/ScriptPage.tsx` | 放大编辑弹窗尺寸 |
| `frontend/src/pages/Report/ReportPage.tsx` | 添加批量删除UI（复选框+操作栏） |
