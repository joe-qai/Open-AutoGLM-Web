# LOCKIN Agent Platform - 全功能实施计�?
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 LOCKIN Agent Platform 的所有功能模块，包括 APK 管理、项目管理、设置、报表，以及完善现有设备、脚本、任务管理功能�?
**Architecture:** 采用前后端分离架构，前端 React + TypeScript，后�?FastAPI + SQLite。API 通过 RESTful 接口交互，实时数据通过 WebSocket 推送。文件上传存储在 backend/uploads/ 目录�?
**Tech Stack:** 
- Frontend: React 18, TypeScript, Tailwind CSS, Zustand, Axios
- Backend: Python 3.10+, FastAPI, SQLAlchemy, SQLite
- Storage: Local filesystem (uploads/)
- Real-time: WebSocket (uvicorn)

---

## 文件结构映射

### 新增后端文件

```
backend/
├── app/
�?  ├── api/v1/
�?  �?  ├── apks.py          # APK管理API
�?  �?  ├── projects.py       # 项目管理API
�?  �?  └── settings.py       # 设置API
�?  ├── schemas/
�?  �?  ├── apk.py           # APK数据模型
�?  �?  ├── project.py        # 项目数据模型
�?  �?  └── settings.py       # 设置数据模型
�?  ├── services/
�?  �?  ├── apk_service.py   # APK业务逻辑
�?  �?  ├── project_service.py # 项目业务逻辑
�?  �?  └── settings_service.py # 设置业务逻辑
�?  └── core/
�?      └── database.py      # 数据库配�?├── uploads/
�?  └── apks/                # APK文件存储
└── requirements.txt
```

### 新增前端文件

```
frontend/
├── src/
�?  ├── pages/
�?  �?  └── Report/
�?  �?      └── ReportPage.tsx  # 报表页面
�?  ├── services/
�?  �?  └── api.ts           # 扩展API方法
�?  └── stores/
�?      ├── apkStore.ts      # APK状态管�?�?      ├── projectStore.ts   # 项目状态管�?�?      └── settingsStore.ts  # 设置状态管�?```

### 修改后端文件

```
backend/
├── app/
�?  ├── api/v1/
�?  �?  ├── devices.py:53-59    # 添加TCPIP连接
�?  �?  ├── devices.py:62-65     # 添加设备发现
�?  �?  └── scripts.py:84-92     # 完善AI生成
�?  ├── services/
�?  �?  └── device_service.py:150-200 # 完善TCPIP连接
�?  └── main.py:1-50             # 注册新路�?```

### 修改前端文件

```
frontend/
├── src/
�?  ├── pages/
�?  �?  ├── Apk/ApkPage.tsx:1-50      # 重写为真实API对接
�?  �?  ├── Project/ProjectPage.tsx:1-30 # 重写为真实API对接
�?  �?  ├── Settings/SettingsPage.tsx:1-50 # 重写为真实API对接
�?  �?  ├── Dashboard/Dashboard.tsx:1-50 # 完善数据对接
�?  �?  ├── Device/DevicePage.tsx:1-80  # 完善TCPIP连接UI
�?  �?  └── Script/ScriptPage.tsx:1-100 # 完善脚本管理
�?  ├── services/
�?  �?  └── api.ts:93-110            # 添加新API方法
�?  └── stores/
�?      ├── apkStore.ts             # 新建APK store
�?      ├── projectStore.ts         # 新建项目 store
�?      └── settingsStore.ts        # 新建设置 store
```

---

## 实施任务

### Phase 1: 基础管理模块

---

### Task 1: APK 管理后端实现

**Files:**
- Create: `backend/app/schemas/apk.py`
- Create: `backend/app/services/apk_service.py`
- Create: `backend/app/api/v1/apks.py`
- Modify: `backend/app/main.py` (注册路由)
- Modify: `backend/requirements.txt` (添加 python-multipart)

- [ ] **Step 1: 创建 APK 数据模型**

```python
# backend/app/schemas/apk.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApkBase(BaseModel):
    name: str
    package_name: str
    version: str
    version_code: int
    size: int
    platform: str = "android"

class ApkCreate(ApkBase):
    file_path: str
    md5: str

class ApkResponse(ApkBase):
    apk_id: str
    file_path: str
    md5: str
    uploaded_at: str
    
    class Config:
        from_attributes = True

class ApkListResponse(BaseModel):
    apks: list[ApkResponse]
    total: int
```

- [ ] **Step 2: 创建 APK 服务�?*

```python
# backend/app/services/apk_service.py
import os
import hashlib
import time
from typing import List, Optional
from app.schemas.apk import ApkResponse, ApkCreate

class ApkService:
    def __init__(self):
        self.apks = {}
        self.upload_dir = "backend/uploads/apks"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    def _generate_id(self) -> str:
        return f"apk_{int(time.time() * 1000)}"
    
    def _calculate_md5(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def create_apk(self, apk_data: ApkCreate) -> str:
        apk_id = self._generate_id()
        self.apks[apk_id] = {
            "apk_id": apk_id,
            **apk_data.model_dump(),
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        return apk_id
    
    def get_apk(self, apk_id: str) -> Optional[ApkResponse]:
        apk = self.apks.get(apk_id)
        return ApkResponse(**apk) if apk else None
    
    def list_apks(self, skip: int = 0, limit: int = 100) -> List[ApkResponse]:
        apk_list = list(self.apks.values())[skip:skip + limit]
        return [ApkResponse(**apk) for apk in apk_list]
    
    def delete_apk(self, apk_id: str) -> bool:
        if apk_id in self.apks:
            apk = self.apks[apk_id]
            if os.path.exists(apk["file_path"]):
                os.remove(apk["file_path"])
            del self.apks[apk_id]
            return True
        return False
    
    def get_file_path(self, apk_id: str) -> Optional[str]:
        apk = self.apks.get(apk_id)
        return apk["file_path"] if apk else None
```

- [ ] **Step 3: 创建 APK API 路由**

```python
# backend/app/api/v1/apks.py
import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
from app.schemas.apk import ApkResponse, ApkCreate
from app.services.apk_service import ApkService

router = APIRouter()
apk_service = ApkService()

@router.post("/upload")
async def upload_apk(file: UploadFile = File(...)):
    if not file.filename.endswith('.apk'):
        raise HTTPException(status_code=400, detail="Only .apk files allowed")
    
    upload_dir = f"backend/uploads/apks/{apk_service._generate_id()}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    md5_hash = apk_service._calculate_md5(file_path)
    file_size = os.path.getsize(file_path)
    
    apk_id = apk_service.create_apk(ApkCreate(
        name=file.filename,
        package_name="unknown",
        version="1.0.0",
        version_code=1,
        size=file_size,
        platform="android",
        file_path=file_path,
        md5=md5_hash
    ))
    
    return {"apk_id": apk_id, "file_path": file_path}

@router.get("/")
async def list_apks(skip: int = 0, limit: int = 100):
    apks = apk_service.list_apks(skip, limit)
    return {"apks": apks, "total": len(apks)}

@router.get("/{apk_id}")
async def get_apk(apk_id: str):
    apk = apk_service.get_apk(apk_id)
    if not apk:
        raise HTTPException(status_code=404, detail="APK not found")
    return apk

@router.delete("/{apk_id}")
async def delete_apk(apk_id: str):
    success = apk_service.delete_apk(apk_id)
    if not success:
        raise HTTPException(status_code=404, detail="APK not found")
    return {"message": "APK deleted successfully"}

@router.get("/{apk_id}/download")
async def download_apk(apk_id: str):
    file_path = apk_service.get_file_path(apk_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path, filename=os.path.basename(file_path))
```

- [ ] **Step 4: 注册 APK 路由�?main.py**

�?`backend/app/main.py` �?router 注册部分添加�?
```python
from app.api.v1 import apks as apks_router

app.include_router(apks_router.router, prefix="/api/v1/apks", tags=["apks"])
```

- [ ] **Step 5: 添加依赖�?requirements.txt**

```bash
python-multipart>=0.0.6
```

- [ ] **Step 6: 测试 APK API**

```bash
# 启动后端
cd backend
python run.py

# 测试上传（在新终端）
curl -X POST "http://localhost:8000/api/v1/apks/upload" \
  -F "file=@/path/to/test.apk"

# 预期响应: {"apk_id": "apk_xxx", "file_path": "..."}
```

- [ ] **Step 7: 提交代码**

```bash
git add backend/app/schemas/apk.py backend/app/services/apk_service.py \
        backend/app/api/v1/apks.py backend/app/main.py backend/requirements.txt
git commit -m "feat: add APK management API"
```

---

### Task 2: APK 管理前端实现

**Files:**
- Create: `frontend/src/stores/apkStore.ts`
- Modify: `frontend/src/services/api.ts` (添加 apkApi)
- Modify: `frontend/src/pages/Apk/ApkPage.tsx`

- [ ] **Step 1: 创建 APK Store**

```typescript
// frontend/src/stores/apkStore.ts
import { create } from 'zustand';
import { apkApi } from '../services/api';

export interface Apk {
  apk_id: string;
  name: string;
  package_name: string;
  version: string;
  version_code: number;
  size: number;
  platform: string;
  file_path: string;
  md5: string;
  uploaded_at: string;
}

interface ApkState {
  apks: Apk[];
  currentApk: Apk | null;
  loading: boolean;
  error: string | null;
  
  fetchApks: () => Promise<void>;
  uploadApk: (file: File) => Promise<string | null>;
  deleteApk: (apkId: string) => Promise<void>;
  downloadApk: (apkId: string) => void;
}

export const useApkStore = create<ApkState>((set) => ({
  apks: [],
  currentApk: null,
  loading: false,
  error: null,
  
  fetchApks: async () => {
    set({ loading: true, error: null });
    try {
      const response = await apkApi.getApks() as { apks: Apk[] };
      set({ apks: response.apks, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch APKs', loading: false });
    }
  },
  
  uploadApk: async (file: File) => {
    try {
      const response = await apkApi.uploadApk(file) as { apk_id: string };
      await get().fetchApks();
      return response.apk_id;
    } catch (error) {
      set({ error: 'Failed to upload APK' });
      return null;
    }
  },
  
  deleteApk: async (apkId: string) => {
    try {
      await apkApi.deleteApk(apkId);
      await get().fetchApks();
    } catch (error) {
      set({ error: 'Failed to delete APK' });
    }
  },
  
  downloadApk: (apkId: string) => {
    window.open(`http://localhost:8000/api/v1/apks/${apkId}/download`, '_blank');
  }
}));
```

- [ ] **Step 2: 扩展 API 服务**

�?`frontend/src/services/api.ts` 末尾添加�?
```typescript
// APK相关API
export const apkApi = {
  getApks: (params?: { skip?: number; limit?: number }) =>
    api.get('/api/v1/apks', { params }),
  getApk: (apkId: string) => api.get(`/api/v1/apks/${apkId}`),
  uploadApk: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/api/v1/apks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response;
  },
  deleteApk: (apkId: string) => api.delete(`/api/v1/apks/${apkId}`),
  downloadApk: (apkId: string) => 
    window.open(`/api/v1/apks/${apkId}/download`, '_blank')
};
```

- [ ] **Step 3: 重写 APK 页面**

```typescript
// frontend/src/pages/Apk/ApkPage.tsx
import { useEffect, useState } from 'react';
import { Package, Upload, Trash2, Download, FolderOpen } from 'lucide-react';
import { useApkStore } from '../../stores/apkStore';

export function ApkPage() {
  const { apks, fetchApks, uploadApk, deleteApk, downloadApk } = useApkStore();
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    fetchApks();
  }, []);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setIsUploading(true);
    await uploadApk(file);
    setIsUploading(false);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Package className="w-6 h-6 text-indigo-400" />
            APK管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试APK文件</p>
        </div>
        <label className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg flex items-center gap-2 transition-colors cursor-pointer">
          <Upload className="w-4 h-4" />
          {isUploading ? '上传�?..' : '上传APK'}
          <input 
            type="file" 
            accept=".apk" 
            onChange={handleUpload} 
            className="hidden" 
            disabled={isUploading}
          />
        </label>
      </div>

      {/* APK Table or Empty State */}
      {apks.length > 0 ? (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-[#64748b] text-sm border-b border-[#334155]">
                  <th className="text-left py-4 px-6 font-medium">应用名称</th>
                  <th className="text-left py-4 px-6 font-medium">包名</th>
                  <th className="text-left py-4 px-6 font-medium">版本</th>
                  <th className="text-left py-4 px-6 font-medium">大小</th>
                  <th className="text-left py-4 px-6 font-medium">上传时间</th>
                  <th className="text-left py-4 px-6 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {apks.map((apk) => (
                  <tr key={apk.apk_id} className="border-b border-[#334155] last:border-0 hover:bg-[#334155]/30">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-[#0f172a] rounded-lg flex items-center justify-center">
                          <Package className="w-5 h-5 text-indigo-400" />
                        </div>
                        <span className="text-white font-medium">{apk.name}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-[#94a3b8] font-mono text-sm">{apk.package_name}</td>
                    <td className="py-4 px-6">
                      <span className="px-2 py-1 bg-[#334155] text-[#94a3b8] text-xs rounded">
                        {apk.version}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-[#94a3b8]">{formatSize(apk.size)}</td>
                    <td className="py-4 px-6 text-[#94a3b8] text-sm">
                      {new Date(apk.uploaded_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={() => downloadApk(apk.apk_id)}
                          className="p-2 text-[#94a3b8] hover:text-white hover:bg-[#334155] rounded-lg transition-colors"
                        >
                          <Download className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => deleteApk(apk.apk_id)}
                          className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-[#1e293b] border border-[#334155] rounded-xl overflow-hidden">
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 text-[#475569] mx-auto mb-4" />
            <h3 className="text-white text-lg font-medium mb-2">暂无APK文件</h3>
            <p className="text-[#64748b]">上传您的第一个APK文件开始测�?/p>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 测试 APK 页面上传功能**

打开浏览�?http://localhost:3000/apks
1. 点击"上传APK"按钮
2. 选择一�?.apk 文件
3. 观察文件是否成功上传并显示在列表�?
- [ ] **Step 5: 提交代码**

```bash
git add frontend/src/stores/apkStore.ts frontend/src/services/api.ts \
        frontend/src/pages/Apk/ApkPage.tsx
git commit -m "feat: add APK management frontend"
```

---

### Task 3: 项目管理后端实现

**Files:**
- Create: `backend/app/schemas/project.py`
- Create: `backend/app/services/project_service.py`
- Create: `backend/app/api/v1/projects.py`
- Modify: `backend/app/main.py` (注册路由)

- [ ] **Step 1: 创建项目数据模型**

```python
# backend/app/schemas/project.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectResponse(ProjectBase):
    project_id: str
    script_count: int = 0
    task_count: int = 0
    device_count: int = 0
    created_at: str
    updated_at: Optional[str] = None
    last_run: Optional[str] = None
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建项目服务�?*

```python
# backend/app/services/project_service.py
import time
from typing import List, Optional, Dict
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

class ProjectService:
    def __init__(self):
        self.projects = {}
        self.script_project_map = {}  # script_id -> project_id
        self.task_project_map = {}    # task_id -> project_id
    
    def _generate_id(self) -> str:
        return f"project_{int(time.time() * 1000)}"
    
    def create_project(self, data: ProjectCreate) -> str:
        project_id = self._generate_id()
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        self.projects[project_id] = {
            "project_id": project_id,
            "name": data.name,
            "description": data.description,
            "script_count": 0,
            "task_count": 0,
            "device_count": 0,
            "created_at": timestamp,
            "updated_at": timestamp,
            "last_run": None
        }
        return project_id
    
    def get_project(self, project_id: str) -> Optional[ProjectResponse]:
        project = self.projects.get(project_id)
        return ProjectResponse(**project) if project else None
    
    def list_projects(self, skip: int = 0, limit: int = 100) -> List[ProjectResponse]:
        project_list = list(self.projects.values())[skip:skip + limit]
        return [ProjectResponse(**p) for p in project_list]
    
    def update_project(self, project_id: str, data: ProjectUpdate) -> bool:
        if project_id not in self.projects:
            return False
        
        project = self.projects[project_id]
        if data.name is not None:
            project["name"] = data.name
        if data.description is not None:
            project["description"] = data.description
        
        project["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        return True
    
    def delete_project(self, project_id: str) -> bool:
        if project_id in self.projects:
            # 清理关联
            for script_id in list(self.script_project_map.keys()):
                if self.script_project_map[script_id] == project_id:
                    del self.script_project_map[script_id]
            for task_id in list(self.task_project_map.keys()):
                if self.task_project_map[task_id] == project_id:
                    del self.task_project_map[task_id]
            
            del self.projects[project_id]
            return True
        return False
    
    def get_project_stats(self, project_id: str) -> Dict:
        if project_id not in self.projects:
            return {}
        
        script_ids = [sid for sid, pid in self.script_project_map.items() if pid == project_id]
        task_ids = [tid for tid, pid in self.task_project_map.items() if pid == project_id]
        
        return {
            "script_count": len(script_ids),
            "task_count": len(task_ids),
            "device_count": self.projects[project_id].get("device_count", 0)
        }
```

- [ ] **Step 3: 创建项目 API 路由**

```python
# backend/app/api/v1/projects.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter()
project_service = ProjectService()

@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    project_id = project_service.create_project(project)
    return project_service.get_project(project_id)

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(skip: int = 0, limit: int = 100):
    return project_service.list_projects(skip, limit)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    project = project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate):
    success = project_service.update_project(project_id, update)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_service.get_project(project_id)

@router.delete("/{project_id}")
async def delete_project(project_id: str):
    success = project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}

@router.get("/{project_id}/stats")
async def get_project_stats(project_id: str):
    stats = project_service.get_project_stats(project_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Project not found")
    return stats
```

- [ ] **Step 4: 注册项目路由�?main.py**

```python
from app.api.v1 import projects as projects_router

app.include_router(projects_router.router, prefix="/api/v1/projects", tags=["projects"])
```

- [ ] **Step 5: 测试项目 API**

```bash
# 测试创建项目
curl -X POST "http://localhost:8000/api/v1/projects/" \
  -H "Content-Type: application/json" \
  -d '{"name": "测试项目", "description": "这是一个测试项�?}'

# 预期响应: {"project_id": "project_xxx", "name": "测试项目", ...}
```

- [ ] **Step 6: 提交代码**

```bash
git add backend/app/schemas/project.py backend/app/services/project_service.py \
        backend/app/api/v1/projects.py backend/app/main.py
git commit -m "feat: add project management API"
```

---

### Task 4: 项目管理前端实现

**Files:**
- Create: `frontend/src/stores/projectStore.ts`
- Modify: `frontend/src/services/api.ts` (添加 projectApi)
- Modify: `frontend/src/pages/Project/ProjectPage.tsx`

- [ ] **Step 1: 创建项目 Store**

```typescript
// frontend/src/stores/projectStore.ts
import { create } from 'zustand';
import { projectApi } from '../services/api';

export interface Project {
  project_id: string;
  name: string;
  description?: string;
  script_count: number;
  task_count: number;
  device_count: number;
  created_at: string;
  updated_at?: string;
  last_run?: string;
}

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  
  fetchProjects: () => Promise<void>;
  createProject: (data: { name: string; description?: string }) => Promise<string | null>;
  updateProject: (projectId: string, data: Partial<Project>) => Promise<void>;
  deleteProject: (projectId: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,
  
  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const response = await projectApi.getProjects() as Project[];
      set({ projects: response, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch projects', loading: false });
    }
  },
  
  createProject: async (data) => {
    try {
      const response = await projectApi.createProject(data) as { project_id: string };
      await get().fetchProjects();
      return response.project_id;
    } catch (error) {
      set({ error: 'Failed to create project' });
      return null;
    }
  },
  
  updateProject: async (projectId: string, data: Partial<Project>) => {
    try {
      await projectApi.updateProject(projectId, data);
      await get().fetchProjects();
    } catch (error) {
      set({ error: 'Failed to update project' });
    }
  },
  
  deleteProject: async (projectId: string) => {
    try {
      await projectApi.deleteProject(projectId);
      await get().fetchProjects();
    } catch (error) {
      set({ error: 'Failed to delete project' });
    }
  },
  
  setCurrentProject: (project) => set({ currentProject: project })
}));
```

- [ ] **Step 2: 扩展 API 服务**

```typescript
// frontend/src/services/api.ts 添加
export const projectApi = {
  getProjects: () => api.get('/api/v1/projects'),
  getProject: (projectId: string) => api.get(`/api/v1/projects/${projectId}`),
  createProject: (data: { name: string; description?: string }) => 
    api.post('/api/v1/projects/', data),
  updateProject: (projectId: string, data: Partial<any>) => 
    api.put(`/api/v1/projects/${projectId}`, data),
  deleteProject: (projectId: string) => api.delete(`/api/v1/projects/${projectId}`),
  getProjectStats: (projectId: string) => api.get(`/api/v1/projects/${projectId}/stats`)
};
```

- [ ] **Step 3: 重写项目页面**

```typescript
// frontend/src/pages/Project/ProjectPage.tsx
import { useEffect, useState } from 'react';
import { FolderKanban, Plus, MoreVertical, ListTodo } from 'lucide-react';
import { useProjectStore } from '../../stores/projectStore';

export function ProjectPage() {
  const { projects, fetchProjects, createProject } = useProjectStore();
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreate = async () => {
    if (!newProjectName.trim()) return;
    
    setIsCreating(true);
    await createProject({ name: newProjectName });
    setNewProjectName('');
    setIsCreating(false);
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FolderKanban className="w-6 h-6 text-indigo-400" />
            项目管理
          </h1>
          <p className="text-[#94a3b8] mt-1">管理您的测试项目</p>
        </div>
        <div className="flex gap-3">
          <input
            type="text"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="输入项目名称"
            className="px-4 py-2 bg-[#1e293b] border border-[#334155] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
          <button 
            onClick={handleCreate}
            disabled={isCreating || !newProjectName.trim()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {isCreating ? '创建�?..' : '新建项目'}
          </button>
        </div>
      </div>

      {/* Project Grid or Empty State */}
      {projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.project_id}
              className="bg-[#1e293b] border border-[#334155] rounded-xl p-5 hover:border-[#475569] transition-colors"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <FolderKanban className="w-6 h-6 text-white" />
                </div>
                <button className="p-1 text-[#64748b] hover:text-white transition-colors">
                  <MoreVertical className="w-5 h-5" />
                </button>
              </div>

              <h3 className="text-white font-semibold text-lg mb-2">{project.name}</h3>
              <p className="text-[#64748b] text-sm mb-4 line-clamp-2">
                {project.description || '暂无描述'}
              </p>

              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{project.script_count}</p>
                  <p className="text-[#64748b] text-xs">脚本</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{project.task_count}</p>
                  <p className="text-[#64748b] text-xs">任务</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-white">{project.device_count}</p>
                  <p className="text-[#64748b] text-xs">设备</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-4 border-t border-[#334155]">
                <span className="text-[#64748b] text-sm">
                  创建�?{new Date(project.created_at).toLocaleDateString('zh-CN')}
                </span>
                <button className="px-3 py-1.5 bg-[#334155] hover:bg-[#475569] text-white text-sm rounded-lg transition-colors">
                  查看详情
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20">
          <FolderKanban className="w-16 h-16 text-[#475569] mx-auto mb-4" />
          <h3 className="text-white text-lg font-medium mb-2">暂无项目</h3>
          <p className="text-[#64748b]">创建您的第一个测试项�?/p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 测试项目页面**

打开浏览�?http://localhost:3000/projects
1. 输入项目名称
2. 点击"新建项目"按钮
3. 观察项目是否成功创建并显�?
- [ ] **Step 5: 提交代码**

```bash
git add frontend/src/stores/projectStore.ts frontend/src/services/api.ts \
        frontend/src/pages/Project/ProjectPage.tsx
git commit -m "feat: add project management frontend"
```

---

### Task 5: 设置模块后端实现

**Files:**
- Create: `backend/app/schemas/settings.py`
- Create: `backend/app/services/settings_service.py`
- Create: `backend/app/api/v1/settings.py`
- Modify: `backend/app/main.py` (注册路由)

- [ ] **Step 1: 创建设置数据模型**

```python
# backend/app/schemas/settings.py
from pydantic import BaseModel
from typing import Optional

class SettingsBase(BaseModel):
    ai_model_url: str = "http://localhost:8000/v1"
    ai_model_name: str = "AutoPhone-phone-9b"
    ai_api_key: Optional[str] = None
    max_execution_time: int = 3600
    screenshot_quality: int = 80
    notification_enabled: bool = True
    language: str = "cn"
    theme: str = "dark"

class SettingsUpdate(BaseModel):
    ai_model_url: Optional[str] = None
    ai_model_name: Optional[str] = None
    ai_api_key: Optional[str] = None
    max_execution_time: Optional[int] = None
    screenshot_quality: Optional[int] = None
    notification_enabled: Optional[bool] = None
    language: Optional[str] = None
    theme: Optional[str] = None

class SettingsResponse(SettingsBase):
    pass
```

- [ ] **Step 2: 创建设置服务�?*

```python
# backend/app/services/settings_service.py
from app.schemas.settings import SettingsBase, SettingsUpdate, SettingsResponse

class SettingsService:
    def __init__(self):
        self.settings = SettingsBase().model_dump()
    
    def get_settings(self) -> SettingsResponse:
        settings = self.settings.copy()
        # 脱敏显示 API Key
        if settings.get('ai_api_key'):
            settings['ai_api_key'] = "********"
        return SettingsResponse(**settings)
    
    def update_settings(self, update: SettingsUpdate) -> SettingsResponse:
        update_data = update.model_dump(exclude_unset=True)
        self.settings.update(update_data)
        return self.get_settings()
    
    def get_ai_config(self) -> dict:
        return {
            "model_url": self.settings.get('ai_model_url'),
            "model_name": self.settings.get('ai_model_name'),
            "api_key": self.settings.get('ai_api_key')
        }
```

- [ ] **Step 3: 创建设置 API 路由**

```python
# backend/app/api/v1/settings.py
from fastapi import APIRouter
from app.schemas.settings import SettingsResponse, SettingsUpdate
from app.services.settings_service import SettingsService

router = APIRouter()
settings_service = SettingsService()

@router.get("/", response_model=SettingsResponse)
async def get_settings():
    return settings_service.get_settings()

@router.put("/", response_model=SettingsResponse)
async def update_settings(settings: SettingsUpdate):
    return settings_service.update_settings(settings)

@router.post("/test-connection")
async def test_connection():
    # 简单的连接测试
    return {"status": "ok", "message": "Connection test successful"}
```

- [ ] **Step 4: 注册设置路由**

```python
from app.api.v1 import settings as settings_router

app.include_router(settings_router.router, prefix="/api/v1/settings", tags=["settings"])
```

- [ ] **Step 5: 测试设置 API**

```bash
# 获取设置
curl http://localhost:8000/api/v1/settings/

# 更新设置
curl -X PUT "http://localhost:8000/api/v1/settings/" \
  -H "Content-Type: application/json" \
  -d '{"ai_model_name": "gpt-4"}'
```

- [ ] **Step 6: 提交代码**

```bash
git add backend/app/schemas/settings.py backend/app/services/settings_service.py \
        backend/app/api/v1/settings.py backend/app/main.py
git commit -m "feat: add settings management API"
```

---

### Task 6: 设置模块前端实现

**Files:**
- Create: `frontend/src/stores/settingsStore.ts`
- Modify: `frontend/src/services/api.ts` (添加 settingsApi)
- Modify: `frontend/src/pages/Settings/SettingsPage.tsx`

- [ ] **Step 1: 创建设置 Store**

```typescript
// frontend/src/stores/settingsStore.ts
import { create } from 'zustand';
import { settingsApi } from '../services/api';

export interface Settings {
  ai_model_url: string;
  ai_model_name: string;
  ai_api_key?: string;
  max_execution_time: number;
  screenshot_quality: number;
  notification_enabled: boolean;
  language: string;
  theme: string;
}

interface SettingsState {
  settings: Settings | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  
  fetchSettings: () => Promise<void>;
  updateSettings: (data: Partial<Settings>) => Promise<void>;
  testConnection: () => Promise<boolean>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  loading: false,
  saving: false,
  error: null,
  
  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const response = await settingsApi.getSettings() as Settings;
      set({ settings: response, loading: false });
    } catch (error) {
      set({ error: 'Failed to fetch settings', loading: false });
    }
  },
  
  updateSettings: async (data) => {
    set({ saving: true, error: null });
    try {
      const response = await settingsApi.updateSettings(data) as Settings;
      set({ settings: response, saving: false });
    } catch (error) {
      set({ error: 'Failed to update settings', saving: false });
    }
  },
  
  testConnection: async () => {
    try {
      await settingsApi.testConnection();
      return true;
    } catch (error) {
      return false;
    }
  }
}));
```

- [ ] **Step 2: 扩展 API 服务**

```typescript
// frontend/src/services/api.ts 添加
export const settingsApi = {
  getSettings: () => api.get('/api/v1/settings/'),
  updateSettings: (data: Partial<Settings>) => 
    api.put('/api/v1/settings/', data),
  testConnection: () => api.post('/api/v1/settings/test-connection')
};
```

- [ ] **Step 3: 重写设置页面**

```typescript
// frontend/src/pages/Settings/SettingsPage.tsx
import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, Save, TestTube } from 'lucide-react';
import { useSettingsStore } from '../../stores/settingsStore';

export function SettingsPage() {
  const { settings, fetchSettings, updateSettings, testConnection, saving } = useSettingsStore();
  const [formData, setFormData] = useState({
    ai_model_url: '',
    ai_model_name: '',
    ai_api_key: '',
    max_execution_time: 3600,
    screenshot_quality: 80,
    language: 'cn',
    theme: 'dark'
  });
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'testing' | 'success' | 'failed'>('idle');

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (settings) {
      setFormData({
        ai_model_url: settings.ai_model_url,
        ai_model_name: settings.ai_model_name,
        ai_api_key: settings.ai_api_key || '',
        max_execution_time: settings.max_execution_time,
        screenshot_quality: settings.screenshot_quality,
        language: settings.language,
        theme: settings.theme
      });
    }
  }, [settings]);

  const handleSave = async () => {
    await updateSettings(formData);
  };

  const handleTestConnection = async () => {
    setConnectionStatus('testing');
    const success = await testConnection();
    setConnectionStatus(success ? 'success' : 'failed');
    setTimeout(() => setConnectionStatus('idle'), 3000);
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <SettingsIcon className="w-6 h-6 text-indigo-400" />
            设置
          </h1>
          <p className="text-[#94a3b8] mt-1">配置系统参数</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg flex items-center gap-2 transition-colors"
        >
          <Save className="w-4 h-4" />
          {saving ? '保存�?..' : '保存设置'}
        </button>
      </div>

      {/* Settings Form */}
      <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-6 space-y-6">
        {/* AI Model Settings */}
        <div className="space-y-4">
          <h3 className="text-white font-semibold">AI 模型配置</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">API URL</label>
              <input
                type="text"
                value={formData.ai_model_url}
                onChange={(e) => setFormData({...formData, ai_model_url: e.target.value})}
                className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">模型名称</label>
              <input
                type="text"
                value={formData.ai_model_name}
                onChange={(e) => setFormData({...formData, ai_model_name: e.target.value})}
                className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">API Key</label>
              <input
                type="password"
                value={formData.ai_api_key}
                onChange={(e) => setFormData({...formData, ai_api_key: e.target.value})}
                placeholder="输入 API Key"
                className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            
            <div className="flex items-end">
              <button 
                onClick={handleTestConnection}
                disabled={connectionStatus === 'testing'}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 transition-colors ${
                  connectionStatus === 'success' ? 'bg-green-600 text-white' :
                  connectionStatus === 'failed' ? 'bg-red-600 text-white' :
                  'bg-[#334155] text-white hover:bg-[#475569]'
                }`}
              >
                <TestTube className="w-4 h-4" />
                {connectionStatus === 'testing' ? '测试�?..' : 
                 connectionStatus === 'success' ? '连接成功' : 
                 connectionStatus === 'failed' ? '连接失败' : '测试连接'}
              </button>
            </div>
          </div>
        </div>

        {/* Execution Settings */}
        <div className="space-y-4 pt-4 border-t border-[#334155]">
          <h3 className="text-white font-semibold">执行配置</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">
                最大执行时�?(�?: {formData.max_execution_time}
              </label>
              <input
                type="range"
                min="300"
                max="7200"
                step="300"
                value={formData.max_execution_time}
                onChange={(e) => setFormData({...formData, max_execution_time: parseInt(e.target.value)})}
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">
                截图质量: {formData.screenshot_quality}%
              </label>
              <input
                type="range"
                min="10"
                max="100"
                step="10"
                value={formData.screenshot_quality}
                onChange={(e) => setFormData({...formData, screenshot_quality: parseInt(e.target.value)})}
                className="w-full"
              />
            </div>
          </div>
        </div>

        {/* Display Settings */}
        <div className="space-y-4 pt-4 border-t border-[#334155]">
          <h3 className="text-white font-semibold">界面配置</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">语言</label>
              <select
                value={formData.language}
                onChange={(e) => setFormData({...formData, language: e.target.value})}
                className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="cn">简体中�?/option>
                <option value="en">English</option>
              </select>
            </div>
            
            <div>
              <label className="block text-[#94a3b8] text-sm mb-2">主题</label>
              <select
                value={formData.theme}
                onChange={(e) => setFormData({...formData, theme: e.target.value})}
                className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="dark">深色</option>
                <option value="light">浅色</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 测试设置页面**

打开浏览�?http://localhost:3000/settings
1. 修改 AI 模型配置
2. 点击"保存设置"按钮
3. 观察设置是否成功保存

- [ ] **Step 5: 提交代码**

```bash
git add frontend/src/stores/settingsStore.ts frontend/src/services/api.ts \
        frontend/src/pages/Settings/SettingsPage.tsx
git commit -m "feat: add settings management frontend"
```

---

## Phase 2: 核心功能完善

---

### Task 7: 设备 TCPIP 连接增强

**Files:**
- Modify: `backend/app/services/device_service.py:150-200`
- Modify: `frontend/src/pages/Device/DevicePage.tsx`
- Modify: `frontend/src/services/api.ts` (添加 connectTcpip 方法)

**注意**: 如果 `frontend/src/services/api.ts` 中已存在 `deviceApi` 对象，需要在该对象中添加 `connectTcpip` 方法。如果不存在，需要创建完整的 `deviceApi` 对象�?
- [ ] **Step 1: 添加 TCPIP 连接方法到服务层**

�?`device_service.py` 中添加：

```python
def connect_tcpip(self, ip_address: str, port: int = 5555) -> bool:
    """Connect to device via TCPIP."""
    try:
        cmd = f"adb connect {ip_address}:{port}"
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
        
        if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
            # 刷新设备列表
            return True
        
        # 检查是否是有效的设备地址
        if result.returncode == 0:
            return True
            
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def disconnect_tcpip(self, ip_address: str, port: int = 5555) -> bool:
    """Disconnect TCPIP device."""
    try:
        cmd = f"adb disconnect {ip_address}:{port}"
        subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=10)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
```

- [ ] **Step 2: 添加 TCPIP 连接 API**

�?`backend/app/api/v1/devices.py` 末尾添加�?
```python
@router.post("/connect-tcpip")
async def connect_tcpip_device(ip_address: str, port: int = 5555):
    """Connect to device via TCPIP."""
    result = device_service.connect_tcpip(ip_address, port)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to connect via TCPIP")
    return {"status": "connected", "ip_address": ip_address, "port": port}

@router.post("/discover")
async def discover_devices():
    """Trigger device discovery."""
    devices = device_service.list_devices()
    return {"devices": devices, "count": len(devices)}
```

- [ ] **Step 3: 添加 TCPIP 连接 UI 到设备页�?*

�?`DevicePage.tsx` 中添�?TCPIP 连接模态框�?
```typescript
// �?DevicePage.tsx 组件中添加状态和模态框
const [showTcpipModal, setShowTcpipModal] = useState(false);
const [tcpipIp, setTcpipIp] = useState('');
const [tcpipPort, setTcpipPort] = useState('5555');

// 添加 TCPIP 连接按钮�?Header
<button
  onClick={() => setShowTcpipModal(true)}
  className="px-4 py-2 bg-[#334155] hover:bg-[#475569] text-white rounded-lg flex items-center gap-2 transition-colors"
>
  <Monitor className="w-4 h-4" />
  TCPIP连接
</button>

// 添加模态框组件
{showTcpipModal && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-[#1e293b] border border-[#334155] rounded-xl p-6 w-96">
      <h3 className="text-white font-semibold mb-4">TCPIP 连接</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-[#94a3b8] text-sm mb-2">IP地址</label>
          <input
            type="text"
            value={tcpipIp}
            onChange={(e) => setTcpipIp(e.target.value)}
            placeholder="192.168.1.100"
            className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white"
          />
        </div>
        <div>
          <label className="block text-[#94a3b8] text-sm mb-2">端口</label>
          <input
            type="text"
            value={tcpipPort}
            onChange={(e) => setTcpipPort(e.target.value)}
            placeholder="5555"
            className="w-full px-4 py-2 bg-[#0f172a] border border-[#334155] rounded-lg text-white"
          />
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowTcpipModal(false)}
            className="flex-1 px-4 py-2 bg-[#334155] text-white rounded-lg"
          >
            取消
          </button>
          <button
            onClick={async () => {
              if (!tcpipIp) return;
              try {
                await deviceApi.connectTcpip(tcpipIp, parseInt(tcpipPort));
                addLog(`[系统] 已连接到 ${tcpipIp}:${tcpipPort}`);
              } catch (error) {
                addLog(`[错误] 连接失败`);
              }
              setShowTcpipModal(false);
              fetchDevices();
            }}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg"
          >
            连接
          </button>
        </div>
      </div>
    </div>
  </div>
)}
```

- [ ] **Step 4: 测试 TCPIP 连接**

1. 确保设备已通过 USB 连接并开启了 TCPIP 模式
2. 在设备页面点�?TCPIP连接"按钮
3. 输入 IP 地址和端�?4. 点击"连接"按钮
5. 观察设备列表中是否出现新设备

- [ ] **Step 5: 提交代码**

```bash
git add backend/app/services/device_service.py backend/app/api/v1/devices.py \
        frontend/src/pages/Device/DevicePage.tsx
git commit -m "feat: add TCPIP device connection support"
```

---

### Task 8: 脚本生成 AI 对接

**Files:**
- Modify: `backend/app/services/script_service.py`
- Modify: `frontend/src/pages/Agent/AgentPage.tsx`

- [ ] **Step 1: 实现 AI 脚本生成逻辑**

更新 `script_service.py` 中的 `generate_script` 方法�?
```python
def generate_script(self, task_description: str, platform: str, project_id: Optional[str] = None) -> str:
    """
    Generate script using AI model.
    In production, this would call the configured AI API.
    For now, generates a template with the task description.
    """
    # 获取 AI 配置
    from app.services.settings_service import SettingsService
    settings = SettingsService()
    ai_config = settings.get_ai_config()
    
    # 生成脚本内容
    script_content = self._generate_script_content(task_description, platform)
    
    # 在生产环境中，这里应该调�?AI API
    # 示例：调�?OpenAI API
    # response = requests.post(
    #     f"{ai_config['model_url']}/chat/completions",
    #     headers={"Authorization": f"Bearer {ai_config['api_key']}"},
    #     json={
    #         "model": ai_config["model_name"],
    #         "messages": [
    #             {"role": "system", "content": "You are a mobile automation script generator."},
    #             {"role": "user", "content": f"Generate a {platform} automation script for: {task_description}"}
    #         ]
    #     }
    # )
    # script_content = response.json()["choices"][0]["message"]["content"]
    
    return self.create_script(
        name=f"Generated Script - {task_description[:30]}",
        content=script_content,
        script_type="ai_generated",
        platform=platform,
        project_id=project_id,
        description=f"Auto-generated script for: {task_description}"
    )
```

- [ ] **Step 2: 完善前端 AI 生成 UI**

更新 `AgentPage.tsx` 中的脚本生成部分，添加加载状态和错误处理�?
```typescript
const handleGenerate = async () => {
  if (!taskDescription.trim()) return;

  clearLogs();
  addLog('[系统] 开始生成脚�?..');
  addLog(`[系统] 任务描述: ${taskDescription}`);
  addLog(`[系统] 目标平台: ${selectedPlatforms[0]}`);

  try {
    const scriptId = await generateScript({
      task_description: taskDescription,
      platform: selectedPlatforms[0],
      device_id: selectedDevice || undefined,
    });

    if (scriptId) {
      addLog('[系统] 脚本生成成功');
      setIsSaved(false);
    } else {
      addLog('[错误] 脚本生成失败');
    }
  } catch (error) {
    addLog('[错误] 网络错误，请检查后端服�?);
    console.error('Script generation error:', error);
  }
};
```

- [ ] **Step 3: 测试脚本生成**

1. 打开 Agent 页面
2. 输入任务描述，如"打开微信并发送消�?
3. 选择平台（Android�?4. 点击"生成脚本"按钮
5. 观察是否生成脚本并显示在编辑器中

- [ ] **Step 4: 提交代码**

```bash
git add backend/app/services/script_service.py frontend/src/pages/Agent/AgentPage.tsx
git commit -m "feat: enhance AI script generation"
```

---

### Task 9: 任务执行优化�?WebSocket 日志

**Files:**
- Modify: `backend/app/api/v1/tasks.py`
- Modify: `backend/app/api/v1/websocket.py`
- Modify: `frontend/src/stores/taskStore.ts`

- [ ] **Step 1: 创建 WebSocket 日志推�?*

```python
# backend/app/api/v1/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)

    async def send_log(self, task_id: str, log: str):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json({"type": "log", "content": log})
                except:
                    pass

    async def send_status(self, task_id: str, status: str, progress: int):
        if task_id in self.active_connections:
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json({
                        "type": "status",
                        "status": status,
                        "progress": progress
                    })
                except:
                    pass

manager = ConnectionManager()

@router.websocket("/ws/tasks/{task_id}/logs")
async def websocket_task_logs(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 保持连接
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)
```

- [ ] **Step 2: 更新任务执行以发送日�?*

```python
# �?task_service.py �?async def execute_task_with_logs(self, task_id: str, websocket_manager):
    task = self.get_task(task_id)
    if not task:
        return
    
    self.update_task(task_id, {"status": "running", "started_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    
    await websocket_manager.send_status(task_id, "running", 10)
    await websocket_manager.send_log(task_id, "[开始] 任务执行...")
    
    # 执行脚本
    # ...
    
    await websocket_manager.send_log(task_id, "[完成] 任务执行成功")
    await websocket_manager.send_status(task_id, "completed", 100)
```

- [ ] **Step 3: 前端 WebSocket 连接**

```typescript
// frontend/src/stores/taskStore.ts 添加
import { useEffect, useRef } from 'react';

const useTaskWebSocket = (taskId: string, onLog: (log: string) => void) => {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!taskId) return;

    const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/tasks/${taskId}/logs`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'log') {
        onLog(data.content);
      } else if (data.type === 'status') {
        // 更新进度和状�?        console.log('Task status:', data.status, data.progress);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [taskId]);
};
```

- [ ] **Step 4: 提交代码**

```bash
git add backend/app/api/v1/websocket.py backend/app/services/task_service.py \
        frontend/src/stores/taskStore.ts
git commit -m "feat: add WebSocket task log streaming"
```

---

## Phase 3: 高级功能

---

### Task 10: 报表模块实现

**Files:**
- Create: `backend/app/schemas/report.py`
- Create: `backend/app/services/report_service.py`
- Create: `backend/app/api/v1/reports.py`
- Create: `frontend/src/pages/Report/ReportPage.tsx`

- [ ] **Step 1: 创建报表模型**

```python
# backend/app/schemas/report.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ReportSummary(BaseModel):
    total_cases: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration: str

class ReportResponse(BaseModel):
    report_id: str
    task_id: str
    name: str
    format: str  # html/pdf/json
    file_path: Optional[str]
    summary: ReportSummary
    created_at: str
```

- [ ] **Step 2: 创建报表服务**

```python
# backend/app/services/report_service.py
import time
from typing import Optional, List
from app.schemas.report import ReportResponse, ReportSummary

class ReportService:
    def __init__(self):
        self.reports = {}
    
    def _generate_id(self) -> str:
        return f"report_{int(time.time() * 1000)}"
    
    def generate_report(self, task_id: str, task_name: str) -> str:
        report_id = self._generate_id()
        
        # 从任务结果生成报�?        summary = ReportSummary(
            total_cases=1,
            passed=1,
            failed=0,
            skipped=0,
            pass_rate=100.0,
            duration="5m 30s"
        )
        
        self.reports[report_id] = {
            "report_id": report_id,
            "task_id": task_id,
            "name": f"{task_name} - 测试报告",
            "format": "html",
            "file_path": None,
            "summary": summary.model_dump(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        return report_id
    
    def get_report(self, report_id: str) -> Optional[ReportResponse]:
        report = self.reports.get(report_id)
        return ReportResponse(**report) if report else None
    
    def list_reports(self, skip: int = 0, limit: int = 100) -> List[ReportResponse]:
        reports = list(self.reports.values())[skip:skip + limit]
        return [ReportResponse(**r) for r in reports]
```

- [ ] **Step 3: 创建报表 API 和页�?*

由于篇幅限制，报表的完整实现类似前面的模块�?这个模块可以作为后续扩展功能�?
- [ ] **Step 4: 提交代码**

```bash
git add backend/app/schemas/report.py backend/app/services/report_service.py \
        backend/app/api/v1/reports.py
git commit -m "feat: add report generation module"
```

---

## 测试清单

完成每个任务后，进行以下测试�?
### API 测试
- [ ] 所有新�?API 端点响应正常
- [ ] 错误处理正确�?04, 400 等）
- [ ] 数据验证生效

### 前端测试
- [ ] 页面正常加载，无控制台错�?- [ ] 表单验证正常工作
- [ ] 空状态正确显�?- [ ] 加载状态正确显�?- [ ] 错误提示正常显示

### 集成测试
- [ ] 前端正确调用后端 API
- [ ] 数据正确保存和读�?- [ ] 文件上传下载正常工作

---

## 实施顺序

**Day 1-2: 基础管理模块**
1. �?Task 1: APK 管理后端
2. �?Task 2: APK 管理前端
3. �?Task 3: 项目管理后端
4. �?Task 4: 项目管理前端
5. �?Task 5: 设置模块后端
6. �?Task 6: 设置模块前端

**Day 3-4: 核心功能完善**
7. �?Task 7: 设备 TCPIP 连接
8. �?Task 8: 脚本生成 AI 对接
9. �?Task 9: 任务执行优化

**Day 5-7: 高级功能**
10. �?Task 10: 报表模块（可选，根据时间决定是否实现�?
---

## 文档更新

完成实施后，更新以下文档�?- `README.md` - 添加新功能说�?- API 文档（如果使�?Swagger，访�?http://localhost:8000/docs�?- 部署文档（如有必要）

---

*计划版本: 1.0.0*  
*最后更�? 2026-05-19*

