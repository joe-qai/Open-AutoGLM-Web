# LLM 配置测试连接功能 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Settings 页面的模型配置弹窗中增加「测试连接」按钮，允许用户在保存前验证 LLM 参数有效性。

**Architecture:** 后端新增 `POST /api/v1/model_configs/test` 端点（复用 ModelConfigCreate 请求体），返回 `{success, message, response_time_ms}`；前端在弹窗底部加测试按钮，表单必填项未填时 disabled，显示连接成功/失败状态。

**Tech Stack:** FastAPI, OpenAI SDK, React, Tailwind CSS, zustand

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/schemas/model_config.py` | Modify (new class) | `ModelConfigTestResponse` |
| `backend/app/services/model_config_service.py` | Modify (new method) | `test_config()` — 创建 SDK client 发测试请求 |
| `backend/app/api/v1/model_configs.py` | Modify (new route) | `POST /test` 路由注册 |
| `frontend/src/services/api.ts` | Modify (new method) | `modelConfigApi.testConfig()` |
| `frontend/src/pages/Settings/SettingsPage.tsx` | Modify (button + state) | 弹窗加测试按钮、状态显示、处理函数 |

---

### Task 1: 新增 `ModelConfigTestResponse` 响应体

**Files:**
- Modify: `backend/app/schemas/model_config.py`

- [ ] **Step 1: 添加 ModelConfigTestResponse schema**

```python
class ModelConfigTestResponse(BaseModel):
    success: bool
    message: str
    response_time_ms: Optional[float] = None
```

在 `ModelConfigCreate` 之后插入。

- [ ] **Step 2: 验证**

Run: `python -c "from app.schemas.model_config import ModelConfigTestResponse; print('OK')"`
Expected: `OK`

---

### Task 2: 实现 `test_config()` 服务方法

**Files:**
- Modify: `backend/app/services/model_config_service.py`

- [ ] **Step 1: 在文件头部添加导入**

```python
import time
import asyncio
from typing import List, Optional
from app.db import db
from app.schemas.model_config import ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse, ModelConfigTestResponse

try:
    from openai import OpenAI
    has_openai = True
except ImportError:
    has_openai = False

try:
    import anthropic
    has_anthropic = True
except ImportError:
    has_anthropic = False
```

注意：保留已有的 `import time`（已有），已有的 `from typing import List, Optional`（已有），只补充需要的导入。

将已有的 `from app.schemas.model_config import ...` 行修改加入 `ModelConfigTestResponse`。

- [ ] **Step 2: 添加 `test_config()` 方法**

```python
async def test_config(self, config: ModelConfigCreate) -> ModelConfigTestResponse:
    provider = config.provider
    if provider.value == "openai":
        if not has_openai:
            return ModelConfigTestResponse(
                success=False,
                message="OpenAI SDK 未安装，请执行 pip install openai"
            )
        return await self._test_openai(config)
    elif provider.value == "anthropic":
        if not has_anthropic:
            return ModelConfigTestResponse(
                success=False,
                message="Anthropic SDK 未安装，请执行 pip install anthropic"
            )
        return await self._test_anthropic(config)
    else:
        return ModelConfigTestResponse(
            success=False,
            message=f"不支持的 provider: {provider.value}"
        )

async def _test_openai(self, config: ModelConfigCreate) -> ModelConfigTestResponse:
    start = time.time()
    try:
        client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=15,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "user", "content": "Respond with exactly: OK"}],
                max_tokens=10,
            )
        )
        elapsed = round((time.time() - start) * 1000)
        if response.choices and response.choices[0].message.content:
            return ModelConfigTestResponse(
                success=True,
                message="连接成功",
                response_time_ms=elapsed,
            )
        else:
            return ModelConfigTestResponse(
                success=False,
                message="响应格式异常",
                response_time_ms=elapsed,
            )
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        msg = self._classify_error(e)
        return ModelConfigTestResponse(
            success=False,
            message=msg,
            response_time_ms=elapsed,
        )

async def _test_anthropic(self, config: ModelConfigCreate) -> ModelConfigTestResponse:
    start = time.time()
    try:
        client = anthropic.Anthropic(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=15,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model=config.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Respond with exactly: OK"}],
            )
        )
        elapsed = round((time.time() - start) * 1000)
        return ModelConfigTestResponse(
            success=True,
            message="连接成功",
            response_time_ms=elapsed,
        )
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        msg = self._classify_error(e)
        return ModelConfigTestResponse(
            success=False,
            message=msg,
            response_time_ms=elapsed,
        )

@staticmethod
def _classify_error(e: Exception) -> str:
    msg = str(e).lower()
    if any(x in msg for x in ["connect", "connection refused", "connection error", "name resolution"]):
        return "无法连接到服务器，请检查 API Base URL"
    if any(x in msg for x in ["401", "unauthorized", "403", "forbidden", "invalid api key", "authentication"]):
        return "API Key 无效或权限不足"
    if any(x in msg for x in ["404", "not found", "model_not_found", "model not found"]):
        return "模型名称不存在"
    if any(x in msg for x in ["timeout", "timed out"]):
        return "连接超时，请检查网络"
    return f"连接失败: {str(e)}"
```

- [ ] **Step 3: 验证导入正确**

Run: `python -c "from app.services.model_config_service import ModelConfigService; print(type(ModelConfigService()._classify_error(Exception('test'))))"`
Expected: `<class 'str'>`

---

### Task 3: 注册 `POST /test` 路由

**Files:**
- Modify: `backend/app/api/v1/model_configs.py`

- [ ] **Step 1: 更新 import 行**

```python
from app.schemas.model_config import ModelConfigResponse, ModelConfigCreate, ModelConfigUpdate, ModelConfigTestResponse
```

- [ ] **Step 2: 添加测试路由（在 `POST /` 之后）**

```python
@router.post("/test", response_model=ModelConfigTestResponse)
async def test_config(config: ModelConfigCreate):
    return await model_config_service.test_config(config)
```

- [ ] **Step 3: 启动后端验证路由注册**

Run: `cd backend && python run.py` 访问 `http://localhost:8000/docs` 确认 `/api/v1/model_configs/test` 出现在文档中（手动确认后 Ctrl+C 停止）

---

### Task 4: 后端单元测试

**Files:**
- Create: `backend/tests/test_model_config_test.py`

- [ ] **Step 1: 编写测试**

```python
"""Tests for model config test endpoint."""

import pytest
from unittest.mock import patch, MagicMock
from app.schemas.model_config import ModelConfigCreate, ModelConfigProvider, ModelConfigTestResponse
from app.services.model_config_service import ModelConfigService


@pytest.fixture
def service():
    return ModelConfigService()


@pytest.mark.asyncio
async def test_test_openai_success(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="gpt-4o",
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "OK"

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_response

        result = await service.test_config(config)

    assert result.success is True
    assert result.message == "连接成功"
    assert result.response_time_ms is not None


@pytest.mark.asyncio
async def test_test_openai_auth_error(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-bad",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import AuthenticationError
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            "Incorrect API key provided",
            response=MagicMock(),
            body=None,
        )

        result = await service.test_config(config)

    assert result.success is False
    assert "API Key" in result.message


@pytest.mark.asyncio
async def test_test_openai_model_not_found(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="nonexistent-model",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import NotFoundError
        mock_client.chat.completions.create.side_effect = NotFoundError(
            "Model not found",
            response=MagicMock(),
            body=None,
        )

        result = await service.test_config(config)

    assert result.success is False
    assert "不存在" in result.message


@pytest.mark.asyncio
async def test_test_openai_timeout(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import APITimeoutError
        mock_client.chat.completions.create.side_effect = APITimeoutError("Request timed out")

        result = await service.test_config(config)

    assert result.success is False
    assert "超时" in result.message


@pytest.mark.asyncio
async def test_test_openai_connection_error(service):
    config = ModelConfigCreate(
        name="test",
        provider="openai",
        base_url="https://invalid-url.com",
        api_key="sk-test",
        model_name="gpt-4o",
    )

    with patch("app.services.model_config_service.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        from openai import APIConnectionError
        mock_client.chat.completions.create.side_effect = APIConnectionError("Connection refused")

        result = await service.test_config(config)

    assert result.success is False
    assert "服务器" in result.message


@pytest.mark.asyncio
async def test_test_unsupported_provider(service):
    config = ModelConfigCreate(
        name="test",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        api_key="sk-ant-test",
        model_name="claude-3-5-sonnet-20240620",
    )

    result = await service.test_config(config)

    # Note: if anthropic SDK is not installed, it should return SDK not installed
    assert result.success is False
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && pytest tests/test_model_config_test.py -v`
Expected: 至少 5 个 test 通过，1 个可能因 anthropic SDK 不存在而和预期一致

---

### Task 5: 前端 API 客户端新增 `testConfig`

**Files:**
- Modify: `frontend/src/services/api.ts`

- [ ] **Step 1: 新增 testConfig 方法**

```typescript
testConfig: (data: any) => api.post('/api/v1/model_configs/test', data),
```

插入到 `modelConfigApi` 对象的 `getDefaultConfig` 之后。

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无 error 输出

---

### Task 6: 前端 SettingsPage 弹窗加测试按钮

**Files:**
- Modify: `frontend/src/pages/Settings/SettingsPage.tsx`
- Reference: `frontend/src/services/api.ts` (import modelConfigApi)

- [ ] **Step 1: 引入 modelConfigApi**

在文件顶部添加导入：
```typescript
import { modelConfigApi } from '../../services/api';
```

- [ ] **Step 2: 添加测试按钮与状态**

在组件内部，`resetForm` 函数之后添加 test 状态：

```typescript
const [testStatus, setTestStatus] = useState<{
  loading: boolean;
  success?: boolean;
  message?: string;
}>({ loading: false });
```

- [ ] **Step 3: 添加测试处理函数**

```typescript
const handleTestConnection = async () => {
  if (testStatus.loading) return;
  setTestStatus({ loading: true });
  try {
    const res: any = await modelConfigApi.testConfig({
      name: name || 'test',
      provider,
      base_url: baseUrl || undefined,
      api_key: apiKey,
      model_name: modelName,
      is_default: false,
    });
    setTestStatus({
      loading: false,
      success: res.success,
      message: res.success
        ? `连接成功 (${res.response_time_ms}ms)`
        : res.message,
    });
  } catch (err: any) {
    setTestStatus({
      loading: false,
      success: false,
      message: err?.response?.data?.detail || '网络请求失败',
    });
  }
};
```

- [ ] **Step 4: 关闭弹窗时重置 testStatus**

在 `handleOpenModal` 的 `setIsModalOpen(true)` 之前加：
```typescript
setTestStatus({ loading: false });
```

在 `handleSubmit` 的 `setIsModalOpen(false)` 之前加：
```typescript
setTestStatus({ loading: false });
```

在弹窗底部 `setIsModalOpen(false)` 的按钮之前加：
```typescript
setTestStatus({ loading: false });
```

- [ ] **Step 5: 弹窗底部按钮区域加测试按钮**

将 `handleSubmit` 按钮同一行的 `flex gap-3 p-6 pt-0` 区域修改为三个按钮（测试-取消-保存）：

```tsx
<div className="flex gap-3 p-6 pt-0">
  <button
    onClick={handleTestConnection}
    disabled={!name || !apiKey || !modelName || testStatus.loading}
    className={`px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm ${
      testStatus.success !== undefined
        ? testStatus.success
          ? 'bg-green-600/20 text-green-400 border border-green-600/30'
          : 'bg-red-600/20 text-red-400 border border-red-600/30'
        : 'bg-[#1e293b] border border-[#334155] text-[#94a3b8] hover:bg-[#334155] hover:text-white'
    } disabled:opacity-50 disabled:cursor-not-allowed`}
  >
    {testStatus.loading ? (
      <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    ) : testStatus.success === true ? (
      <Check className="w-4 h-4" />
    ) : testStatus.success === false ? (
      <X className="w-4 h-4" />
    ) : null}
    {testStatus.loading ? '测试中...' : testStatus.message || '测试连接'}
  </button>
  <button
    onClick={() => setIsModalOpen(false)}
    className="flex-1 px-4 py-2.5 bg-[#334155] hover:bg-[#475569] text-white rounded-lg transition-colors"
  >
    取消
  </button>
  <button
    onClick={handleSubmit}
    disabled={!name || !apiKey || !modelName}
    className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
  >
    <Save className="w-4 h-4" />
    保存
  </button>
</div>
```

- [ ] **Step 6: 验证编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 7: 验证渲染（可选，手动）**

Run: `cd frontend && npm run dev`
Expected: 打开 Settings 弹窗，填入必填项后测试按钮可点击，点击后显示 loading → 成功/失败

---

### 自检清单

1. Spec 覆盖：`POST /api/v1/model_configs/test` 端点 ✓，ModelConfigTestResponse ✓，错误分类中文消息 ✓，弹窗测试按钮 ✓，表单字段未填 disabled ✓，成功绿色/失败红色 ✓，response_time_ms 显示 ✓
2. 无占位符 ✓
3. 类型一致性：Service 方法返回 `ModelConfigTestResponse`，API 路由 `response_model=ModelConfigTestResponse`，前端接受 `res.success / res.message / res.response_time_ms` — 一致 ✓
