# 项目增强 (Projects/BatchDelete/Openpyxl) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement three independent enhancements: remove platform restriction from projects, optimize task batch delete UX (always-visible checkboxes), and fix missing openpyxl dependency for script execution.

**Architecture:** Three independent changes across backend and frontend. Project platform removal touches backend schemas, API, service layer and frontend ProjectPage/Store. Batch delete UX reshapes TaskPage checkbox/footer pattern to match ReportPage's always-visible approach. Openpyxl is a single-line dependency add.

**Tech Stack:** FastAPI + SQLite (backend), React + Zustand + Tailwind (frontend)

---

### Task 1: 后端 - Project schemas 移除 platform

**Files:**
- Modify: `backend/app/schemas/project.py:1-34`

- [ ] **Step 1: Remove platform from ProjectBase**

Current:
```python
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    platform: PlatformType
```

Replace with:
```python
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
```

- [ ] **Step 2: Remove platform from ProjectUpdate**

Current:
```python
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    platform: Optional[PlatformType] = None
```

Replace with:
```python
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
```

- [ ] **Step 3: Remove PlatformType import**

Remove line: `from app.schemas.device import PlatformType`

---

### Task 2: 后端 - Project API 移除 platform 参数

**Files:**
- Modify: `backend/app/api/v1/projects.py:1-51`

- [ ] **Step 1: Remove platform query param from list_projects**

Current:
```python
@router.get("/")
async def list_projects(platform: PlatformType | None = None):
    projects = await project_service.list_projects(platform)
    return {"projects": projects}
```

Replace with:
```python
@router.get("/")
async def list_projects():
    projects = await project_service.list_projects()
    return {"projects": projects}
```

- [ ] **Step 2: Remove PlatformType import**

Remove line: `from app.schemas.device import PlatformType`

- [ ] **Step 3: Remove platform type annotations from imports**

The `PlatformType` import removal is covered by Step 2. The `project_service.list_projects` call no longer passes any argument.

---

### Task 3: 后端 - Project service 移除 platform 逻辑

**Files:**
- Modify: `backend/app/services/project_service.py:1-83`

- [ ] **Step 1: Remove PlatformType import**

Remove line: `from app.schemas.device import PlatformType`

- [ ] **Step 2: Change create_project to NOT require platform**

Current (lines 18-29):
```python
await conn.execute(
    """INSERT INTO projects (project_id, name, description, platform, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)""",
    (project_id, project_create.name, project_create.description,
     project_create.platform or "android", now, now)
)
await conn.commit()
return Project(project_id=project_id, name=project_create.name,
               description=project_create.description,
               platform=project_create.platform or "android",
               created_at=datetime.fromisoformat(now),
               updated_at=datetime.fromisoformat(now))
```

Replace with (hardcode `"cross"` since DB column keeps existing but we ignore platform):
```python
await conn.execute(
    """INSERT INTO projects (project_id, name, description, platform, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)""",
    (project_id, project_create.name, project_create.description,
     "cross", now, now)
)
await conn.commit()
return Project(project_id=project_id, name=project_create.name,
               description=project_create.description,
               platform="cross",
               created_at=datetime.fromisoformat(now),
               updated_at=datetime.fromisoformat(now))
```

- [ ] **Step 3: list_projects no longer filters by platform**

Current (lines 42-53):
```python
async def list_projects(self, platform: Optional[PlatformType] = None) -> List[Project]:
    conn = await db.get_connection()
    if platform:
        cursor = await conn.execute("SELECT * FROM projects WHERE platform = ? ORDER BY created_at DESC", (platform,))
    else:
        cursor = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
    ...
```

Replace with:
```python
async def list_projects(self) -> List[Project]:
    conn = await db.get_connection()
    cursor = await conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
    ...
```

- [ ] **Step 4: update_project no longer handles platform**

Current (lines 68-70):
```python
if project_update.platform is not None:
    fields.append("platform = ?")
    values.append(project_update.platform)
```

Remove these 3 lines.

- [ ] **Step 5: Clean up imports**

Remove `Optional` from import if it's no longer used (the function signatures no longer use it). Check if it's used elsewhere in the file — `get_project` still returns `Optional[Project]`, so `Optional` stays.

---

### Task 4: 前端 - projectStore 移除 platform

**Files:**
- Modify: `frontend/src/stores/projectStore.ts:1-82`

- [ ] **Step 1: Remove platform from Project interface**

Current:
```typescript
export interface Project {
  project_id: string;
  name: string;
  description: string;
  platform?: 'android' | 'ios' | 'harmonyos' | 'cross';
  created_at: string;
  updated_at: string;
  task_count?: number;
}
```

Replace with:
```typescript
export interface Project {
  project_id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  task_count?: number;
}
```

- [ ] **Step 2: Remove platform from createProject/updateProject types**

Current:
```typescript
createProject: (data: {
  name: string;
  description: string;
  platform?: string;
}) => Promise<void>;
updateProject: (projectId: string, data: {
  name?: string;
  description?: string;
  platform?: string;
}) => Promise<void>;
```

Replace with:
```typescript
createProject: (data: {
  name: string;
  description: string;
}) => Promise<void>;
updateProject: (projectId: string, data: {
  name?: string;
  description?: string;
}) => Promise<void>;
```

---

### Task 5: 前端 - ProjectPage 移除 platform UI

**Files:**
- Modify: `frontend/src/pages/Project/ProjectPage.tsx:1-234`

- [ ] **Step 1: Remove platform from formData initial state**

Current:
```typescript
const [formData, setFormData] = useState({
  name: '',
  description: '',
  platform: 'android' as const,
});
```

Replace with:
```typescript
const [formData, setFormData] = useState({
  name: '',
  description: '',
});
```

- [ ] **Step 2: Remove platform from handleCreateProject reset**

Current:
```typescript
setFormData({ name: '', description: '', platform: 'android' });
```

Replace with:
```typescript
setFormData({ name: '', description: '' });
```

- [ ] **Step 3: Remove platform from handleEditProject**

Current:
```typescript
setFormData({
  name: project.name,
  description: project.description,
  platform: (project.platform || 'android') as any,
});
```

Replace with:
```typescript
setFormData({
  name: project.name,
  description: project.description,
});
```

- [ ] **Step 4: Remove getPlatformBadge function and its callsite**

Remove the entire `getPlatformBadge` function (lines 45-57).

In the project card template (around lines 101-103), remove:
```tsx
<div className="flex items-center gap-2 mt-1">
  {getPlatformBadge(project.platform)}
  {project.task_count !== undefined && (
    ...
  )}
</div>
```

Replace with:
```tsx
{project.task_count !== undefined && (
  <span className="text-[#64748b] text-sm mt-1">{project.task_count} 个任务</span>
)}
```

- [ ] **Step 5: Remove platform selector from modal form**

Remove the entire platform select section (lines 198-210):
```tsx
<div>
  <label className="block text-[#94a3b8] text-sm mb-2">平台</label>
  <select
    value={formData.platform}
    onChange={(e) => setFormData({ ...formData, platform: e.target.value as any })}
    className="w-full bg-[#0f172a] border border-[#334155] rounded-lg py-2.5 px-4 text-white focus:outline-none focus:border-indigo-500"
  >
    <option value="android">Android</option>
    <option value="ios">iOS</option>
    <option value="harmonyos">HarmonyOS</option>
    <option value="cross">跨平台</option>
  </select>
</div>
```

- [ ] **Step 6: Clean unused imports**

After removing the modal, check if `Plus, Trash2, Check, X, Edit, MoreVertical` are still used (>90% likely yes). `RefreshCw` stays. No import changes needed.

---

### Task 6: 前端 - TaskPage 批量删除 UX 重构

**Files:**
- Modify: `frontend/src/pages/Task/TaskPage.tsx:1-539`

This is the most complex change. The current UX has a `batchMode` toggle (enter batch mode → see checkboxes → select → delete). The desired UX (like ReportPage) always shows checkboxes and shows a toolbar only when items are selected.

- [ ] **Step 1: Remove batchMode state, keep only selectedTaskIds**

Current:
```typescript
const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());
const [batchMode, setBatchMode] = useState(false);
```

Replace with:
```typescript
const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set());
```

- [ ] **Step 2: Simplify header buttons — always show "新增任务"**

Current (`batchMode ?` ternary, lines 183-219):
```tsx
{batchMode ? (
  <>
    <span className="text-[#94a3b8] text-sm">{selectedTaskIds.size} 已选择</span>
    <button onClick={handleBatchDeleteClick} ...>批量删除</button>
    <button onClick={() => { setBatchMode(false); setSelectedTaskIds(new Set()); }}>取消</button>
  </>
) : (
  <>
    <button onClick={() => { setBatchMode(true); setSelectedTaskIds(new Set()); }}>批量删除</button>
    <button onClick={() => setIsModalOpen(true)}>新增任务</button>
  </>
)}
```

Replace with (only the "新增任务" button):
```tsx
<button
  onClick={() => setIsModalOpen(true)}
  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors"
>
  <Plus className="w-4 h-4" />
  新增任务
</button>
```

- [ ] **Step 3: Remove batchMode from select-all th condition**

Current (lines 228-238):
```tsx
{batchMode && (
  <th className="text-left py-4 px-4 font-medium w-10">
    <button onClick={toggleSelectAllTasks} className="text-[#94a3b8] hover:text-white transition-colors">
      ...
    </button>
  </th>
)}
```

Replace with (always show checkbox column in thead):
```tsx
<th className="text-left py-4 px-4 font-medium w-10">
  <button onClick={toggleSelectAllTasks} className="text-[#94a3b8] hover:text-white transition-colors">
    {selectedTaskIds.size === tasks.length && tasks.length > 0 ? (
      <CheckSquare className="w-4 h-4" />
    ) : (
      <Square className="w-4 h-4" />
    )}
  </button>
</th>
```

- [ ] **Step 4: Remove batchMode from each row checkbox td**

Current (lines 257-267):
```tsx
{batchMode && (
  <td className="py-4 px-4">
    <button onClick={() => toggleTaskSelect(task.task_id)} className="text-[#94a3b8] hover:text-white transition-colors">
      ...
    </button>
  </td>
)}
```

Replace with (always show checkbox in rows):
```tsx
<td className="py-4 px-4">
  <button onClick={() => toggleTaskSelect(task.task_id)} className="text-[#94a3b8] hover:text-white transition-colors">
    {selectedTaskIds.has(task.task_id) ? (
      <CheckSquare className="w-4 h-4 text-indigo-400" />
    ) : (
      <Square className="w-4 h-4" />
    )}
  </button>
</td>
```

- [ ] **Step 5: Add batch action toolbar (between header and table)**

Add this block between the `</div>` of header (line 219) and the `<div className="bg-[#1e293b]...">` of table (line 223):

```tsx
{selectedTaskIds.size > 0 && (
  <div className="mb-4 p-3 bg-indigo-900/30 border border-indigo-500/30 rounded-lg flex items-center justify-between">
    <span className="text-indigo-300 font-medium">已选择 {selectedTaskIds.size} 项</span>
    <div className="flex gap-2">
      <button
        onClick={handleBatchDeleteClick}
        disabled={batchDeleting}
        className="px-4 py-1.5 bg-red-600 hover:bg-red-500 disabled:bg-red-800 text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
      >
        {batchDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
        {batchDeleting ? '删除中...' : '批量删除'}
      </button>
      <button
        onClick={() => setSelectedTaskIds(new Set())}
        className="px-4 py-1.5 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg flex items-center gap-1.5 transition-colors"
      >
        <X className="w-4 h-4" />
        取消选择
      </button>
    </div>
  </div>
)}
```

- [ ] **Step 6: Update handleConfirmBatchDelete**

Remove `setBatchMode(false)` from the cleanup (line 164):

Current:
```typescript
const handleConfirmBatchDelete = async () => {
  setConfirmOpen(false);
  setBatchDeleting(true);
  try {
    await useTaskStore.getState().batchDeleteTasks(Array.from(selectedTaskIds));
    setSelectedTaskIds(new Set());
    setBatchMode(false);
  } catch (error) {
    console.error('Batch delete failed:', error);
  } finally {
    setBatchDeleting(false);
  }
};
```

Replace with:
```typescript
const handleConfirmBatchDelete = async () => {
  setConfirmOpen(false);
  setBatchDeleting(true);
  try {
    await useTaskStore.getState().batchDeleteTasks(Array.from(selectedTaskIds));
    setSelectedTaskIds(new Set());
  } catch (error) {
    console.error('Batch delete failed:', error);
  } finally {
    setBatchDeleting(false);
  }
};
```

- [ ] **Step 7: Clean up unused imports**

Check if `CheckSquare, Square, X` are already imported. They should be from the existing import line. Add `CheckSquare` and `Square` to the import from lucide-react if missing.

Current import: `import { ListTodo, Play, Square, CheckSquare, Trash2, Clock, CheckCircle2, XCircle, Loader2, Plus, X, Bot, Upload, ChevronDown, ChevronUp, FileText } from 'lucide-react';`

`Square`, `CheckSquare`, `X` — all present. No changes needed.

---

### Task 7: 安装 openpyxl

**Files:**
- Modify: `backend/requirements.txt:1-30`

- [ ] **Step 1: Add openpyxl to requirements**

Add after line 15 (`httpx==0.27.0`):
```
openpyxl>=3.1.0
```

- [ ] **Step 2: Install openpyxl in backend venv**

Run: `pip install openpyxl`

Use the venv's pip at `backend/.venv/Scripts/pip` or the system pip if using a global venv. Determine the correct pip path first.

```bash
# Find and activate the backend venv, then install
pip install openpyxl
```

---

### Verification

- [ ] **Run ruff lint check**

```bash
ruff check --fix .
ruff format .
```

- [ ] **Run backend smoke test**

```bash
cd backend
# Start the server briefly and test endpoints
uvicorn app.main:app --port 8001 &
# Test project creation without platform
curl -X POST http://localhost:8001/api/v1/projects/ -H "Content-Type: application/json" -d '{"name":"Test","description":"No platform"}'
# Kill server
kill %1
```

- [ ] **Confirm frontend compiles**

```bash
cd frontend
npm run build  # or whatever the build command is
```
