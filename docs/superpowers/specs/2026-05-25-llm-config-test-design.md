# LLM 配置测试连接功能设计

## 目标

在 LLM 模型配置的管理界面中增加「测试连接」入口，让用户可以在保存配置前验证 LLM 参数（base_url、api_key、model_name）是否正确、服务是否可达。

---

## 后端：测试 API

### 端点

`POST /api/v1/model_configs/test`

### 请求体

复用 `ModelConfigCreate` schema：

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 配置名称（仅用于请求标识） |
| provider | "openai" \| "anthropic" | 服务商 |
| base_url | str | API 地址（必填，测试用） |
| api_key | str | API 密钥 |
| model_name | str | 模型名称 |

### 响应体

新 schema `ModelConfigTestResponse`：

| 字段 | 类型 | 说明 |
|------|------|------|
| success | bool | 是否连通 |
| message | str | 中文结果描述 |
| response_time_ms | float \| null | 响应耗时（毫秒） |

### 实现逻辑

1. 根据 `provider` 创建对应的 SDK client（OpenAI / Anthropic）
2. 发送最小测试请求：`[{"role": "user", "content": "Respond with exactly: OK"}]`，`max_tokens=10`
3. 记录耗时
4. 异常情况分类处理（返回中文 message）：

| 异常类型 | message |
|----------|---------|
| `connect_error` / 连接拒绝 | 无法连接到服务器，请检查 API Base URL |
| 401 / 403 | API Key 无效或权限不足 |
| 404 / model_not_found | 模型名称不存在 |
| timeout | 连接超时，请检查网络 |
| 其他 | 具体错误描述 |

### 文件变更

- `backend/app/schemas/model_config.py` — 新增 `ModelConfigTestResponse`
- `backend/app/services/model_config_service.py` — 新增 `test_config(ModelConfigCreate) -> ModelConfigTestResponse`
- `backend/app/api/v1/model_configs.py` — 注册 `POST /test` 路由

---

## 前端：测试按钮

### 位置

SettingsPage 中「新增/编辑模型配置」弹窗底部，紧贴「保存」按钮左侧。

### 交互流程

1. 弹窗中的表单字段（name、apiKey、modelName）未填满时，按钮为 disabled 灰色
2. 点击 → 按钮显示 loading 旋转图标，文字变为「测试中...」
3. 成功 → 绿色 ✓ + "连接成功 (342ms)"，持续显示直到下次点击或关闭弹窗
4. 失败 → 红色 ✗ + 具体错误消息
5. 测试结果不影响表单提交；用户可以随时点击再次测试

### 状态管理

使用组件内 `useState`，不经过 zustand store：

```typescript
const [testStatus, setTestStatus] = useState<{
  loading: boolean;
  success?: boolean;
  message?: string;
}>({ loading: false });
```

### API 调用

通过 `api.ts` 已有 axios 实例，新增方法：

```typescript
testConfig: (data: ModelConfigCreate) => api.post('/api/v1/model_configs/test', data)
```

### 文件变更

- `frontend/src/services/api.ts` — 新增 `testConfig` 方法
- `frontend/src/pages/Settings/SettingsPage.tsx` — 弹窗底部加按钮 + 状态 + 处理函数

---

## 不变的内容

- ModelConfigCreate / ModelConfigResponse schema 不改
- zustand modelConfigStore 不改
- AgentPage / TaskPage 不改
- 后端不设新的 config_id 生成逻辑

---

## 错误处理

后端：
- SDK 初始化异常 → `{"success": false, "message": "客户端初始化失败: ..."}`
- 请求异常 → 按类型映射到中文消息（见上表）
- 响应内容非预期 → 不计入成功，返回 `{"success": false, "message": "响应格式异常"}`
- 超时保护：请求设置 15s timeout

前端：
- 网络断连 → 按钮状态恢复，显示 "网络请求失败"
- 弹窗关闭 → 重置 testStatus
- 多次点击 → 上次请求未完成时忽略新点击

---

## 测试

后端：
- Mock OpenAI client 返回正常响应 → `success=true`
- Mock 抛出 `AuthenticationError` → `success=false`, message 含 API Key 提示
- Mock 抛出 `APITimeoutError` → `success=false`, message 含超时提示
- 无效 provider → `success=false`, message 含 provider 提示

前端：
- 测试按钮 disabled 状态随表单字段变化
- 成功/失败消息渲染
- loading 状态按钮不可重复点击
