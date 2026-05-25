# UI Optimization & Device Info Fix

## Overview

Four small-to-medium changes across the web platform: fix device info display bug (backend), compact LLM config cards, compact device detail drawer, and expose project card operations directly.

## 1. Device Info `getprop` Fix

**File**: `backend/app/services/device_service.py`

**Problem**: `_get_device_info()` uses `adb shell getprop` (returns ALL props) then parses lines with `re.search(r'\[(.+)\]', line)`. The greedy regex captures `ro.product.model]: [Pixel 7 Pro` instead of just `Pixel 7 Pro`, corrupting the value.

**Solution**: Replace the bulk getprop + regex approach with individual `adb shell getprop <key>` commands. Each command returns just the value with no parsing needed.

```python
# Before
output = self._run_adb_command("shell getprop", device_id)
for line in output.split('\n'):
    if 'ro.product.model' in line:
        match = re.search(r'\[(.+)\]', line)
        if match:
            info["model"] = match.group(1)
    # ... similar for manufacturer, os_version ...

# After
info["model"] = self._run_adb_command("shell getprop ro.product.model", device_id).strip()
info["manufacturer"] = self._run_adb_command("shell getprop ro.product.manufacturer", device_id).strip()
info["os_version"] = self._run_adb_command("shell getprop ro.build.version.release", device_id).strip()
info["android_sdk_version"] = self._run_adb_command("shell getprop ro.build.version.sdk", device_id).strip()
```

This also eliminates the `import re` dependency and makes the code more maintainable. The `_get_device_info` test should be updated accordingly.

## 2. LLM Config Card Compact

**File**: `frontend/src/pages/Settings/SettingsPage.tsx`

**Current**: `p-6`, 3 vertical info rows, action buttons hidden behind `opacity-0 group-hover:opacity-100`.

**Changes**:
- Padding `p-6` → `p-4`
- Merge model + base_url into one row (model name on the left, base URL truncated on the right)
- API Key row stays but margin reduced
- Make action buttons always visible (remove `opacity-0 group-hover:opacity-100` from the button group, keep same icon-only style)
- Default badge size stays the same

Layout before (tall):
```
┌──────────────────────┐
│ [icon] Name  [⚡✏️🗑️] │  ← buttons hidden
│        provider       │
│ 模型: gpt-4o         │
│ 地址: https://...     │
│ API Key: ••••••••••   │
└──────────────────────┘
```

Layout after (compact):
```
┌─────────────────────────┐
│ [icon] Name  [⚡✏️🗑️]    │  ← always visible
│        provider          │
│ 模型: gpt-4o | 地址: URL  │  ← merged row
│ API Key: •••••••••••••   │
└─────────────────────────┘
```

## 3. Device Detail Drawer Compact

**File**: `frontend/src/components/DeviceDetailDrawer.tsx`

**Current**: All sections use `p-4` padding. Screenshot image has no height limit, can cause vertical scroll.

**Changes**:
- All `p-4` → `p-3` (info section, screenshot section, action buttons)
- Screenshot `<img>` gets `max-h-[200px] object-contain` to cap height
- Remove `overflow-y-auto` from the drawer panel — content should fit without scroll at typical screen heights
- Keep `overflow-y-auto` only as fallback for very short viewports (add `max-h-screen`)

These changes eliminate the need to scroll the drawer for most use cases.

## 4. Project Card Visible Operations

**File**: `frontend/src/pages/Project/ProjectPage.tsx`

**Current**: Edit/delete buttons are inside a `⋮` (MoreVertical) dropdown that appears on hover.

**Changes**:
- Remove the `⋮` button and its dropdown menu entirely
- Add edit and delete icon buttons directly in the card header area (top-right), matching the LLM config card pattern
- Buttons use the same styling: `p-2 text-indigo-400 hover:bg-indigo-500/10` (edit) and `p-2 text-red-400 hover:bg-red-500/10` (delete)
- Buttons are always visible, no hover reveal needed

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/device_service.py` | Replace bulk getprop with individual calls, remove regex |
| `backend/tests/test_device_service.py` | Update test for new getprop approach |
| `frontend/src/pages/Settings/SettingsPage.tsx` | Compact LLM card: p-4, merged rows, always-visible buttons |
| `frontend/src/components/DeviceDetailDrawer.tsx` | Compact padding, capped screenshot height, remove overflow scroll |
| `frontend/src/pages/Project/ProjectPage.tsx` | Expose edit/delete directly on card |

## Testing

- Backend: run `pytest tests/test_device_service.py` — existing tests should pass
- LLM test: `pytest tests/test_model_config_test.py` — 10 tests must pass
- Frontend: `npm run dev` and visually verify each page
  - LLM cards show compact layout with always-visible buttons
  - Device drawer has no scrollbar at 768px+ viewport height
  - Project cards show edit/delete icons directly

## Not In Scope

- No new features, no new API endpoints
- No changes to device-project data model
- No changes to backend LLM test logic (already working)
