# AutoPhone 安装与部署指南

## 目录

- [一、项目概述](#一项目概述)
- [二、公共环境准备](#二公共环境准备)
- [三、Android 环境配置](#三android-环境配置)
- [四、HarmonyOS 环境配置](#四harmonyos-环境配置)
- [五、iOS 环境配置](#五ios-环境配置)
- [六、模型部署](#六模型部署)
- [七、phone_agent 执行方式](#七phone_agent-执行方式)

---

## 一、项目概述

AutoPhone 是智谱 AI 开发的手机端智能助理框架，基于视觉语言模型（VLM）理解手机屏幕内容，通过 ADB/HDC/XCTest 控制设备实现自动化操作。支持 **Android**、**HarmonyOS**、**iOS** 三大平台。

### 核心模型

| 模型 | 下载链接 |
|------|---------|
| AutoPhone-Phone-9B（中文优化） | [HuggingFace](https://huggingface.co/zai-org/AutoPhone-Phone-9B) / [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B) |
| AutoPhone-Phone-9B-Multilingual（多语言） | [HuggingFace](https://huggingface.co/zai-org/AutoPhone-Phone-9B-Multilingual) / [ModelScope](https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B-Multilingual) |

---

## 二、公共环境准备

### 1. Python 环境

```bash
# Python 3.10+ required
python --version

# 安装依赖
pip install -r requirements.txt
pip install -e .
```

### 2. 设备控制工具

| 平台 | 工具 | 安装方式 |
|------|------|---------|
| Android | ADB | [官方下载](https://developer.android.com/tools/releases/platform-tools) |
| HarmonyOS | HDC | [HarmonyOS SDK](https://developer.huawei.com/consumer/cn/download/) |
| iOS | libimobiledevice | `brew install libimobiledevice` |

**环境变量配置示例（macOS）：**

```bash
# ADB (假设解压到 ~/Downloads/platform-tools)
export PATH=${PATH}:~/Downloads/platform-tools

# HDC
export PATH=${PATH}:~/Downloads/harmonyos-sdk/toolchains
```

---

## 三、Android 环境配置

### 3.1 设备要求

- Android 7.0+ 设备
- 启用开发者模式
- 启用 USB 调试

### 3.2 启用开发者模式

找到 `设置 > 关于手机 > 版本号`，连续快速点击约 **10 次**，直到弹出提示"开发者模式已启用"。

> 不同手机操作方法可能略有差异，如找不到可上网搜索教程。

### 3.3 启用 USB 调试

启用开发者模式后，进入 `设置 > 开发者选项 > USB 调试`，勾选开启。

**请务必仔细检查以下权限：**

![Android 权限配置](resources/screenshot-20251209-181423.png)

### 3.4 安装 ADB Keyboard（用于文本输入）

ADB Keyboard 是 Android 设备文本输入所必需的组件：

```bash
# 1. 下载 ADB Keyboard APK
# 下载地址: https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk

# 2. 安装到设备
adb install ADBKeyboard.apk

# 3. 启用 ADB Keyboard 输入法
adb shell ime enable com.android.adbkeyboard/.AdbIME
adb shell ime set com.android.adbkeyboard/.AdbIME
```

> **注意**：安装完成后还需到 `设置 > 输入法` 或 `设置 > 键盘列表` 中启用 ADB Keyboard 才能生效。

### 3.5 验证连接

```bash
# 检查设备连接
adb devices

# 预期输出：
# List of devices attached
# emulator-5554   device
```

> **注意**：请确保 USB 数据线支持数据传输功能（而非仅充电）。

### 3.6 远程调试（WiFi 连接）

#### 步骤 1：在手机端开启无线调试

确保手机和电脑在同一个 WiFi 网络中，进入 `设置 > 开发者选项 > 无线调试`，勾选开启。

![开启无线调试](resources/setting.png)

#### 步骤 2：在电脑端连接

```bash
# 通过 WiFi 连接（替换为手机显示的 IP 地址和端口）
adb connect 192.168.1.100:5555

# 验证连接
adb devices
# 应显示：192.168.1.100:5555    device
```

#### 启用 TCP/IP 模式（通过 USB）

```bash
# 在 USB 连接状态下启用 TCP/IP 模式
adb tcpip 5555

# 然后拔掉 USB，通过 WiFi 连接
adb connect 192.168.1.100:5555
```

---

## 四、HarmonyOS 环境配置

### 4.1 设备要求

- HarmonyOS NEXT 版本以上设备
- 启用开发者模式
- 启用 USB 调试 + 无线调试

### 4.2 启用开发者模式

找到 `设置 > 关于手机 > 版本号`，连续快速点击约 **10 次**，直到弹出提示"开发者模式已启用"。

### 4.3 启用 USB 调试和无线调试

进入 `设置 > 开发者选项`，勾选：
- **USB 调试**
- **无线调试**

记录显示的 **IP 地址和端口号**。

### 4.4 验证连接

```bash
# 检查设备
hdc list targets

# 预期输出：
# 7001005458323933328a01bce01c2500
```

### 4.5 远程调试（WiFi 连接）

```bash
# 通过 WiFi 连接
hdc tconn 192.168.1.100:5555

# 验证连接
hdc list targets
# 应显示：192.168.1.100:5555
```

---

## 五、iOS 环境配置

### 5.1 环境要求

- **macOS** 操作系统
- **Xcode**（App Store 下载最新版本）
- **苹果开发者账号**（免费账号即可，无需付费）
- **iOS 设备**（iPhone/iPad）
- **USB 数据线**或同一 WiFi 网络

### 5.2 安装 WebDriverAgent

WebDriverAgent 是 iOS 自动化的核心组件，需要在 iOS 设备上运行。

```bash
# 克隆 WebDriverAgent
git clone https://github.com/appium/WebDriverAgent.git
cd WebDriverAgent

# 使用 Xcode 打开项目
open WebDriverAgent.xcodeproj
```

### 5.3 Xcode 配置签名

#### 设置 Signing & Capabilities

1. 在 Xcode 中选中 `WebDriverAgent` 项目
2. 进入 `Signing & Capabilities` 选项卡
3. 勾选 `Automatically manage signing`
4. 在 Team 中选择自己的开发者账号
5. 将 Bundle ID 改为唯一标识符，例如：`com.yourname.WebDriverAgentRunner`

![iOS 签名配置](docs/ios_setup/resources/ios0_WebDriverAgent0.png)

6. **重要**：建议将以下三个 Target 的签名都按相同方式设置：
   - WebDriverAgentLib
   - WebDriverAgentRunner
   - IntegrationApp

![iOS Target 签名配置](docs/ios_setup/resources/ios0_WebDriverAgent1.png)

### 5.4 部署到设备

#### 通过 USB 连接

1. 从 Xcode Target 中选择 `WebDriverAgentRunner`
2. 选择你的 iOS 设备

![选择 iOS 设备](docs/ios_setup/resources/select-your-iphone-device.png)

3. 长按运行按钮（▶️），选择 "Test" 开始编译并部署到 iPhone

![开始测试](docs/ios_setup/resources/start-wda-testing.png)

#### 部署成功的标志

1. Xcode 没有报错
2. iPhone 上出现名为 **WebDriverAgentRunner** 的 App
3. 屏幕显示 "Automation Running" 字样

### 5.5 设备信任配置

首次运行时需要在 iPhone 上完成以下设置：

1. **输入解锁密码**
2. **信任开发者 App**
   - 进入：`设置 > 通用 > VPN与设备管理`
   - 在"开发者 App"中选择对应开发者
   - 点击"信任"

![信任开发者 App](docs/ios_setup/resources/trust-dev-app.jpg)

3. **启用 UI 自动化**
   - 进入：`设置 > 开发者选项`
   - 打开"UI 自动化"设置

![启用 UI 自动化](docs/ios_setup/resources/enable-ui-automation.jpg)

### 5.6 命令行模式

#### 安装 libimobiledevice

```bash
brew install libimobiledevice

# 检查设备连接
idevice_id -ln
```

#### 端口映射（USB 模式）

```bash
iproxy 8100 8100
```

#### 命令行构建

```bash
cd WebDriverAgent

xcodebuild -project WebDriverAgent.xcodeproj \
           -scheme WebDriverAgentRunner \
           -destination 'platform=iOS,name=YOUR_PHONE_NAME' \
           test
```

> 注意：`YOUR_PHONE_NAME` 可以在 Xcode 的设备列表中看到。

#### 获取 WDA URL

构建成功后，Xcode 控制台会输出类似信息：

```
ServerURLHere->http://[设备IP]:8100<-ServerURLHere
```

其中 **`http://[设备IP]:8100`** 为 WiFi 连接所需的 WDA_URL。

### 5.7 常见问题排查

| 问题 | 解决方案 |
|------|---------|
| 无法连接设备 | 检查 USB 是否支持数据传输，确认已信任此电脑 |
| WDA 无法启动 | 确保设备已信任开发者，重启 WebDriverAgentRunner |
| 端口被占用 | 使用 `lsof -i :8100` 检查端口占用情况 |

---

## 六、模型部署

### 6.1 方案 A：使用第三方模型服务（推荐）

| 服务商 | Base URL | Model Name | 文档 |
|--------|----------|------------|------|
| 智谱 BigModel | `https://open.bigmodel.cn/api/paas/v4` | `AutoPhone-phone` | [文档](https://docs.bigmodel.cn/cn/api/introduction) |
| ModelScope | `https://api-inference.modelscope.cn/v1` | `ZhipuAI/AutoPhone-Phone-9B` | [文档](https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B) |

**使用示例：**

```bash
# 智谱 BigModel
python main.py \
    --base-url https://open.bigmodel.cn/api/paas/v4 \
    --model "AutoPhone-phone" \
    --apikey "your-bigmodel-api-key" \
    "打开美团搜索附近的火锅店"

# ModelScope
python main.py \
    --base-url https://api-inference.modelscope.cn/v1 \
    --model "ZhipuAI/AutoPhone-Phone-9B" \
    --apikey "your-modelscope-api-key" \
    "打开美团搜索附近的火锅店"
```

### 6.2 方案 B：本地部署模型

#### 安装推理引擎

**vLLM 安装：**

```bash
pip install vllm>=0.12.0
pip install -U transformers --pre
```

**SGLang 安装：**

```bash
pip install sglang>=0.5.6.post1
pip install nvidia-cudnn-cu12==9.16.0.29
```

> **注意**：上述依赖冲突可以忽略。

#### vLLM 部署命令

```bash
python3 -m vllm.entrypoints.openai.api_server \
 --served-model-name AutoPhone-phone-9b \
 --allowed-local-media-path / \
 --mm-encoder-tp-mode data \
 --mm_processor_cache_type shm \
 --mm_processor_kwargs "{\"max_pixels\":5000000}" \
 --max-model-len 25480 \
 --chat-template-content-format string \
 --limit-mm-per-prompt "{\"image\":10}" \
 --model zai-org/AutoPhone-Phone-9B \
 --port 8000
```

#### SGLang 部署命令

```bash
python3 -m sglang.launch_server \
 --model-path zai-org/AutoPhone-Phone-9B \
 --served-model-name AutoPhone-phone-9b \
 --context-length 25480 \
 --mm-enable-dp-encoder \
 --mm-process-config '{"image":{"max_pixels":5000000}}' \
 --port 8000
```

> **注意**：该模型结构与 `GLM-4.1V-9B-Thinking` 相同，详细部署说明可参考 [GLM-V](https://github.com/zai-org/GLM-V)。

#### Docker 部署（可选）

**vLLM Docker：**

```bash
docker pull vllm/vllm-openai:v0.12.0
docker run -p 8000:8000 \
    --vllm-openai:v0.12.0 \
    python3 -m vllm.entrypoints.openai.api_server \
    --served-model-name AutoPhone-phone-9b \
    --allowed-local-media-path / \
    --mm-encoder-tp-mode data \
    --mm_processor_cache_type shm \
    --mm_processor_kwargs "{\"max_pixels\":5000000}" \
    --max-model-len 25480 \
    --chat-template-content-format string \
    --limit-mm-per-prompt "{\"image\":10}" \
    --model zai-org/AutoPhone-Phone-9B
```

**SGLang Docker：**

```bash
docker pull lmsysorg/sglang:v0.5.6.post1
docker run -p 8000:8000 \
    lmsysorg/sglang:v0.5.6.post1 \
    python3 -m sglang.launch_server \
    --model-path zai-org/AutoPhone-Phone-9B \
    --served-model-name AutoPhone-phone-9b \
    --context-length 25480 \
    --mm-enable-dp-encoder \
    --mm-process-config '{"image":{"max_pixels":5000000}}'
```

### 6.3 验证部署

```bash
python scripts/check_deployment_cn.py \
 --base-url http://你的IP:8000/v1 \
 --model AutoPhone-phone-9b
```

脚本将发送测试请求并展示模型的推理结果。如果思维链长度很短或出现乱码，很可能是模型部署失败。

---

## 七、phone_agent 执行方式

### 7.1 命令行使用

#### Android 设备

```bash
# 交互模式
python main.py --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b"

# 执行指定任务
python main.py --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 使用 API Key
python main.py --apikey sk-xxxxx --base-url https://open.bigmodel.cn/api/paas/v4 --model "AutoPhone-phone"

# 英文模式
python main.py --lang en --base-url http://localhost:8000/v1 "Open Chrome browser"

# 列出支持的应用
python main.py --list-apps

# 远程设备
python main.py --device-id 192.168.1.100:5555 --base-url http://localhost:8000/v1 "任务"
```

#### HarmonyOS 设备

```bash
# 指定设备类型为 hdc
python main.py --device-type hdc --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b"

# 指定任务
python main.py --device-type hdc --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 列出支持的应用
python main.py --device-type hdc --list-apps
```

#### iOS 设备

```bash
# 指定设备类型为 ios
python main.py --device-type ios \
    --base-url http://localhost:8000/v1 \
    --wda-url http://localhost:8100 \
    "Open Safari and search"

# 使用 WiFi 连接（设备 IP）
python main.py --device-type ios \
    --wda-url http://192.168.1.100:8100 \
    "你的任务"

# 检查 WDA 状态
python main.py --device-type ios --wda-status

# 列出 iOS 设备
python main.py --device-type ios --list-devices
```

#### iOS 专用脚本

```bash
python ios.py \
    --base-url "YOUR_BASE_URL" \
    --model "AutoPhone-phone" \
    --api-key "YOUR_API_KEY" \
    --wda-url http://localhost:8100 \
    "你的任务"
```

### 7.2 Python API 使用

```python
from phone_agent import PhoneAgent
from phone_agent.agent import AgentConfig
from phone_agent.model import ModelConfig

# 配置模型
model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="AutoPhone-phone-9b",
    api_key="EMPTY",
)

# 配置 Agent
agent_config = AgentConfig(
    max_steps=100,        # 最大步数
    device_id=None,       # None 为自动检测
    lang="cn",            # cn 或 en
    format="pseudo",      # pseudo 或 json
    verbose=True,         # 打印详细输出
)

# 创建 Agent
agent = PhoneAgent(
    model_config=model_config,
    agent_config=agent_config,
)

# 执行任务
result = agent.run("打开淘宝搜索无线耳机")
print(result)
```

### 7.3 远程连接 Python API

#### Android 设备

```python
from phone_agent.adb import ADBConnection, list_devices

conn = ADBConnection()

# 连接远程设备
success, message = conn.connect("192.168.1.100:5555")
print(f"连接状态: {message}")

# 列出设备
devices = list_devices()
for device in devices:
    print(f"{device.device_id} - {device.connection_type.value}")

# 启用 TCP/IP
success, message = conn.enable_tcpip(5555)
ip = conn.get_device_ip()
print(f"设备 IP: {ip}")

# 断开连接
conn.disconnect("192.168.1.100:5555")
```

#### HarmonyOS 设备

```python
from phone_agent.hdc import HDCConnection, list_devices

conn = HDCConnection()

# 连接远程设备
success, message = conn.connect("192.168.1.100:5555")
print(f"连接状态: {message}")

# 列出设备
devices = list_devices()
for device in devices:
    print(f"{device.device_id} - {device.connection_type.value}")

# 断开连接
conn.disconnect("192.168.1.100:5555")
```

### 7.4 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PHONE_AGENT_BASE_URL` | `http://localhost:8000/v1` | 模型 API 地址 |
| `PHONE_AGENT_MODEL` | `AutoPhone-phone-9b` | 模型名称 |
| `PHONE_AGENT_API_KEY` | `EMPTY` | API Key |
| `PHONE_AGENT_MAX_STEPS` | `100` | 单任务最大步数 |
| `PHONE_AGENT_DEVICE_ID` | 自动检测 | 设备 ID |
| `PHONE_AGENT_DEVICE_TYPE` | `adb` | 设备类型（adb/hdc/ios） |
| `PHONE_AGENT_LANG` | `cn` | 语言（cn/en） |
| `PHONE_AGENT_FORMAT` | `pseudo` | 输出格式（pseudo/json） |
| `PHONE_AGENT_WDA_URL` | `http://localhost:8100` | iOS WDA 地址 |

### 7.5 Verbose 模式

启用 `verbose=True` 时，Agent 会输出每一步的详细推理过程：

```
==================================================
💭 思考过程
--------------------------------------------------
当前在系统桌面，需要先启动小红书应用
--------------------------------------------------
🎯 执行动作:
{
  "_metadata": "do",
  "action": "Launch",
  "app": "小红书"
}
==================================================

==================================================
💭 思考过程
--------------------------------------------------
小红书已打开，现在需要点击搜索框
--------------------------------------------------
🎯 执行动作:
{
  "_metadata": "do",
  "action": "Tap",
  "element": [500, 100]
}
==================================================

🎉 ================================================
✅ 任务完成: 已成功搜索美食攻略
==================================================
```

---

## 八、架构说明

### 核心模块结构

```
phone_agent/
├── agent.py           # Android/HarmonyOS Agent 主类
├── agent_ios.py       # iOS Agent 主类
├── device_factory.py # 设备抽象工厂（DeviceFactory）
├── actions/
│   ├── handler.py     # Android/HarmonyOS 动作执行器
│   └── handler_ios.py # iOS 动作执行器
├── model/
│   └── client.py      # 模型客户端（支持 OpenAI 兼容 API）
├── adb/               # Android ADB 实现
│   ├── connection.py
│   ├── device.py
│   ├── input.py
│   └── screenshot.py
├── hdc/               # HarmonyOS HDC 实现
│   ├── connection.py
│   ├── device.py
│   ├── input.py
│   └── screenshot.py
└── xctest/            # iOS XCTest 实现
    ├── connection.py
    ├── device.py
    ├── input.py
    └── screenshot.py
```

### Agent 执行流程

```
截图 → 检测当前 App → 构建多模态消息 → 调用 VLM → 解析动作 → 执行动作 → 循环直到完成
```

### 支持的动作类型

| 动作 | 说明 |
|------|------|
| `Launch` | 启动应用 |
| `Tap` | 点击坐标 |
| `Swipe` | 滑动 |
| `Type` | 文本输入 |
| `Back` | 返回 |
| `Home` | 主页 |
| `Wait` | 等待 |
| `Take_over` | 人工接管 |
| `Call_API` | 调用外部 API |
| `Interact` | 交互操作 |

---

## 九、常见问题

### Android

| 问题 | 解决方案 |
|------|---------|
| 设备未找到 | 运行 `adb kill-server && adb start-server`，检查 USB 调试是否开启 |
| 能打开应用但无法点击 | 在 `设置 > 开发者选项` 中同时启用"USB 调试"和"USB 调试（安全设置）" |
| 文本输入不工作 | 确保 ADB Keyboard 已安装并在 `设置 > 系统 > 语言和输入法` 中启用 |
| Windows 编码异常 | 运行前添加环境变量 `PYTHONIOENCODING=utf-8` |

### iOS

| 问题 | 解决方案 |
|------|---------|
| 设备未连接 | 确保已信任开发者，运行 `idevice_id -l` 验证 |
| WebDriverAgent 无响应 | 重启 Xcode 中的 WebDriverAgentRunner，检查端口映射 |
| 无法获取 WDA URL | 确保 WebDriverAgent 成功运行，查看 Xcode 控制台输出 |

### HarmonyOS

| 问题 | 解决方案 |
|------|---------|
| 设备未找到 | 检查 HDC 是否安装并配置环境变量，确认 USB 调试已开启 |
| 远程连接失败 | 确保设备与电脑在同一网络，检查防火墙设置 |

---

## 十、相关资源

- [项目 GitHub](https://github.com/zai-org/AutoPhone)
- [Midscene.js 接入指南](https://midscenejs.com/zh/model-common-config.html#auto-glm)
- [GLM-V 模型部署指南](https://github.com/zai-org/GLM-V)
- [WebDriverAgent 官方仓库](https://github.com/appium/WebDriverAgent)
