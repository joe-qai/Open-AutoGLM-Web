# UI Optimization & Device Info Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix device info `getprop` parsing bug and compact three frontend views (LLM card, device drawer, project card).

**Architecture:** Backend fix in DeviceService `_get_device_info()` — replace bulk `getprop` with individual calls. Three independent frontend layout changes in SettingsPage, DeviceDetailDrawer, and ProjectPage.

**Tech Stack:** Python (FastAPI) backend, React 18 + TypeScript + Tailwind frontend.

---

### Task 1: Fix `_get_device_info()` getprop parsing

**Files:**
- Modify: `backend/app/services/device_service.py:57-98`
- Modify: `backend/app/services/device_service.py:1` (remove `import re`)

- [ ] **Step 1: Read current method**

Read `backend/app/services/device_service.py` lines 57-98 to see the current implementation.

- [ ] **Step 2: Replace bulk getprop with individual calls**

```python
# In _get_device_info(), replace lines 76-98 with:

        # Get model, manufacturer, OS version, SDK version, device type
        info["model"] = self._run_adb_command("shell getprop ro.product.model", device_id).strip()
        info["manufacturer"] = self._run_adb_command("shell getprop ro.product.manufacturer", device_id).strip()
        info["os_version"] = self._run_adb_command("shell getprop ro.build.version.release", device_id).strip()
        info["android_sdk_version"] = self._run_adb_command("shell getprop ro.build.version.sdk", device_id).strip()
        info["device_type"] = self._run_adb_command("shell getprop ro.build.characteristics", device_id).strip()
```

- [ ] **Step 3: Remove unused `import re`**

From the top of `device_service.py`, remove the line `import re` (or the existing `import re` if present).

- [ ] **Step 4: Add a test for `_get_device_info`**

Add to `backend/tests/test_device_service.py`:

```python
class TestGetDeviceInfo:
    """Verify _get_device_info reads props via individual getprop commands."""

    def test_get_device_info_individual_getprop_calls(self, device_service):
        """Each property should be fetched with a separate adb getprop command."""
        expected_values = {
            "shell getprop ro.product.model": "Pixel 7 Pro",
            "shell getprop ro.product.manufacturer": "Google",
            "shell getprop ro.build.version.release": "15",
            "shell getprop ro.build.version.sdk": "35",
            "shell getprop ro.build.characteristics": "tablet",
        }

        with patch.object(device_service, '_run_adb_command') as mock_run:
            def side_effect(cmd, device_id):
                return expected_values.get(cmd, "")
            mock_run.side_effect = side_effect

            info = device_service._get_device_info("test123")

        assert info["model"] == "Pixel 7 Pro"
        assert info["manufacturer"] == "Google"
        assert info["os_version"] == "15"
        assert info["android_sdk_version"] == "35"
        assert info["device_type"] == "tablet"
        assert info["name"] == "Pixel 7 Pro"  # name is derived from model
```

- [ ] **Step 5: Run the test**

```bash
cd backend
$env:PYTHONPATH="C:\pythonworkspace\Open-AutoGLM\backend"; pytest tests/test_device_service.py::TestGetDeviceInfo -v
```

Expected: PASS

- [ ] **Step 6: Run all device service tests**

```bash
cd backend
$env:PYTHONPATH="C:\pythonworkspace\Open-AutoGLM\backend"; pytest tests/test_device_service.py -v
```

Expected: all existing tests still PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/device_service.py backend/tests/test_device_service.py
git commit -m "fix: use individual adb getprop calls for device info"
```

---

### Task 2: Compact LLM Config Card

**Files:**
- Modify: `frontend/src/pages/Settings/SettingsPage.tsx` (card component)

- [ ] **Step 1: Read the card component**

Read the card JSX in `frontend/src/pages/Settings/SettingsPage.tsx` (around lines 176-252).

- [ ] **Step 2: Reduce padding and merge info rows**

Make these changes to the card:

1. `p-6` → `p-4` on the outer div
2. `space-y-2` → `space-y-1.5` on the info container
3. Merge model + base_url into one flex row:
```tsx
<div className="space-y-1.5">
  <div className="flex items-center gap-2 text-sm">
    <div className="flex items-center gap-2 flex-1 min-w-0">
      <Server className="w-4 h-4 text-[#475569] shrink-0" />
      <span className="text-[#94a3b8] shrink-0">模型:</span>
      <span className="text-[#e2e8f0] truncate">{config.model_name}</span>
    </div>
    {config.base_url && (
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <Globe className="w-4 h-4 text-[#475569] shrink-0" />
        <span className="text-[#94a3b8] shrink-0">地址:</span>
        <span className="text-[#e2e8f0] truncate">{config.base_url}</span>
      </div>
    )}
  </div>
  <div className="flex items-center gap-2 text-sm">
    <Key className="w-4 h-4 text-[#475569]" />
    <span className="text-[#94a3b8]">API Key:</span>
    <span className="text-[#e2e8f0]">••••••••••••</span>
  </div>
</div>
```
4. Remove `opacity-0 group-hover:opacity-100` from the action button group, make them always visible with slightly lower opacity (`opacity-60 hover:opacity-100`)

- [ ] **Step 3: Verify the frontend compiles**

```bash
cd frontend
npm run build 2>&1 | head -20
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Settings/SettingsPage.tsx
git commit -m "refactor: compact LLM config card layout"
```

---

### Task 3: Compact Device Detail Drawer

**Files:**
- Modify: `frontend/src/components/DeviceDetailDrawer.tsx`

- [ ] **Step 1: Read the drawer**

Read `frontend/src/components/DeviceDetailDrawer.tsx`.

- [ ] **Step 2: Compact padding and cap screenshot height**

Changes:

1. All section `p-4` → `p-3` (device info, screenshot, action buttons)
2. Screenshot img: add `max-h-[200px] object-contain`
3. On the drawer panel div, change `overflow-y-auto` to `max-h-screen overflow-y-auto` (keep overflow as fallback but constrain height)

```tsx
// Line 61: drawer panel div
<div className="fixed right-0 top-0 h-full w-[400px] bg-[#1e293b] border-l border-[#334155] z-50 animate-slide-in-right max-h-screen overflow-y-auto">

// Line 80: device info section
<div className="p-3 border-b border-[#334155]">

// Line 133: screenshot section
<div className="p-3 border-b border-[#334155]">

// Line 150: screenshot img
<img ... className="w-full rounded-lg border border-[#334155] max-h-[200px] object-contain" />

// Line 164: action buttons
<div className="p-3">
```

- [ ] **Step 3: Verify build**

```bash
cd frontend
npm run build 2>&1 | head -20
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DeviceDetailDrawer.tsx
git commit -m "refactor: compact device detail drawer padding and screenshot"
```

---

### Task 4: Expose Project Card Operations

**Files:**
- Modify: `frontend/src/pages/Project/ProjectPage.tsx`

- [ ] **Step 1: Read the project card component**

Read `frontend/src/pages/Project/ProjectPage.tsx` lines 74-122.

- [ ] **Step 2: Replace dropdown menu with direct icon buttons**

Replace lines 93-113 (the `MoreVertical` dropdown group):

```tsx
// Before (the dropdown menu):
<div className="relative group">
  <button className="p-1 hover:bg-[#334155] rounded-lg transition-colors">
    <MoreVertical className="w-4 h-4 text-[#64748b]" />
  </button>
  <div className="absolute right-0 top-0 mt-8 w-32 bg-[#1e293b] border border-[#334155] rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
    <button onClick={() => handleEditProject(project)} title="编辑" className="...">
      <Edit className="w-4 h-4" />
    </button>
    <button onClick={() => deleteProject(project.project_id)} title="删除" className="...">
      <Trash2 className="w-4 h-4" />
    </button>
  </div>
</div>

// After (direct icon buttons):
<div className="flex items-center gap-1">
  <button
    onClick={() => handleEditProject(project)}
    className="p-2 text-indigo-400 hover:bg-indigo-500/10 rounded-lg transition-colors"
    title="编辑"
  >
    <Edit className="w-4 h-4" />
  </button>
  <button
    onClick={() => deleteProject(project.project_id)}
    className="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
    title="删除"
  >
    <Trash2 className="w-4 h-4" />
  </button>
</div>
```

Also remove unused `MoreVertical` import from the top of the file (line 2).

- [ ] **Step 3: Verify build**

```bash
cd frontend
npm run build 2>&1 | head -20
```

Expected: Build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Project/ProjectPage.tsx
git commit -m "refactor: expose project card edit/delete as direct icon buttons"
```
