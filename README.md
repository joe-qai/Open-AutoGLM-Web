# AutoPhone

[Readme in English](README_en.md)

<div align="center">
<img src=resources/logo.svg width="20%"/>
</div>
<p align="center">
    👋 加入我们？<a href="resources/WECHAT.md" target="_blank">微信</a> 社区
</p>
<p align="center">
    👋 关注智谱 AI 输入法？<a href="https://x.com/Autotyper_Agent?s=20" target="_blank">X</a> 账号
</p>
<p align="center">
    🎤 进一步在我们的产品？<a href="https://AutoPhone.zhipuai.cn/autotyper/" target="_blank">智谱 AI 输入法</a> 体验"用嘴发指令"
</p>
<p align="center">
    <a href="https://mp.weixin.qq.com/s/wRp22dmRVF23ySEiATiWIQ" target="_blank">AutoPhone 实战</a> 开发者激励活动火热进行中，跑通、二创即可瓜分数万元现金奖池！成果提交👉 <a href="https://zhipu-ai.feishu.cn/share/base/form/shrcnE3ZuPD5tlOyVJ7d5Wtir8c?from=navigation" target="_blank">入口</a>
</p>

## 懒人版快速安装

你可以使用Claude Code，配置[GLM Coding Plan](https://bigmodel.cn/glm-coding) 后，输入以下提示词，快速部署本项目：

```
访问文档，为我安装AutoPhone
https://raw.githubusercontent.com/zai-org/AutoPhone/refs/heads/main/README.md
```

## 项目介绍

Phone Agent 是一个基于AutoPhone 构建的手机端智能助理框架，它能够以多模态方式理解手机屏幕内容，并通过自动化操作帮助用户完成任务。系统通过
ADB(Android Debug Bridge)来控制设备，以视觉语言模型进行屏幕感知，再结合智能规划能力生成并执行操作流程。用户只需用自然语言描述需求，如"打开小红书搜索美食"，Phone
Agent 即可自动解析意图、理解当前界面、规划下一步动作并完成整个流程。系统还内置敏感操作确认机制，并支持在登录或验证码场景下进行人工接管。同时，它提供远程
ADB 调试能力，可通过 WiFi 或网络连接设备，实现灵活的远程控制与开发。

> ⚠️
> 本项目仅供研究和学习使用。严禁用于非法获取信息、干扰系统或任何违法活动。请仔细审阅 [使用条款](resources/privacy_policy.txt)。

## 与其他自动化工具集成

### Midscene.js

[Midscene.js](https://midscenejs.com/zh/index.html) 是一款由视觉模型驱动的开源UI自动化SDK，支持通过 JavaScript 和 Yaml 格式的流程语法，实现多平台的自动化测试。

目前 Midscene.js 已完成对 AutoPhone 模型的适配，你可以通过 [Midscene.js 接入指南](https://midscenejs.com/zh/model-common-config.html#auto-glm) 快速体验AutoPhone 在 iOS 和 Android 设备上的自动化效果。

## 模型下载地址

| Model                         | Download Links                                                                                                                                                         |
|-------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| AutoPhone-Phone-9B              | [🤗 Hugging Face](https://huggingface.co/zai-org/AutoPhone-Phone-9B)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B)                           |
| AutoPhone-Phone-9B-Multilingual | [🤗 Hugging Face](https://huggingface.co/zai-org/AutoPhone-Phone-9B-Multilingual)<br>[🤖 ModelScope](https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B-Multilingual) |

其中，`AutoPhone-Phone-9B` 是针对中文手机应用优化的模型，`AutoPhone-Phone-9B-Multilingual` 支持英语场景，适用于包含英文等其他语言内容的应用。

## Android 环境准备

### 1. Python 环境

建议使用 Python 3.10 及以上版本。

### 2. 手机调试命令行工具

根据你的设备类型选择相应的工具：

#### 对于 Android 设备 - 使用 ADB

1. 下载官方 ADB [安装包](https://developer.android.com/tools/releases/platform-tools?hl=zh-cn)，并解压到自定义路径
2. 配置环境变量

- MacOS 配置方法：在 `Terminal` 或者任何命令行工具中

  ```bash
  # 假设解压后的目录是 ~/Downloads/platform-tools。如果不是请自行调整命令
  export PATH=${PATH}:~/Downloads/platform-tools
  ```

- Windows 配置方法：可参考[第三方教程](https://blog.csdn.net/x2584179909/article/details/108319973) 进行配置。

#### 对于鸿蒙设备 (HarmonyOS NEXT版本以上) - 使用 HDC

1. 下载 HDC 工具
   - 从 [HarmonyOS SDK](https://developer.huawei.com/consumer/cn/download/) 下载
2. 配置环境变量

- MacOS/Linux 配置方法：

  ```bash
  # 假设解压后的目录是 ~/Downloads/harmonyos-sdk/toolchains。请根据实际路径调整
  export PATH=${PATH}:~/Downloads/harmonyos-sdk/toolchains
  ```

- Windows 配置方法：将 HDC 工具所在目录添加到系统 PATH 环境变量

### 3. Android 7.0+ 或 HarmonyOS 设备，并启用 `开发者模式` 以及 `USB 调试`

1. 开发者模式启用：通常启用方法是，找到 `设置-关于手机-版本号` 然后连续快速点击约 10
   次左右，直到弹出弹窗显示"开发者模式已启用"。不同手机会有些许差别，如果找不到，可以上网搜索一下教程。
2. USB 调试启用：启用开发者模式之后，会出现 `设置-开发者选项-USB 调试`，勾选启用。
3. 部分机型在设置开发者选项以后, 可能需要重启设备才能生效 可以测试一下 将手机用USB数据线连接到电脑后 `adb devices`
   查看是否有设备信息。如果 没有说明连接失败.

**请务必仔细检查相关权限**

![权限](resources/screenshot-20251209-181423.png)

### 4. 安装 ADB Keyboard(仅Android 设备需要，用于文本输入)

**注意：鸿蒙设备使用原生输入方法，无需安装 ADB Keyboard。**

如果你使用的是 Android 设备：

下载 [安装包](https://github.com/senzhk/ADBKeyBoard/blob/master/ADBKeyboard.apk) 并在对应的安卓设备中进行安装。
注意，安装完成后还需要到 `设置-输入法` 或者 `设置-键盘列表` 中启用 `ADB Keyboard` 才能生效(或使用命令 `adb shell ime enable com.android.adbkeyboard/.AdbIME`[How-to-use](https://github.com/senzhk/ADBKeyBoard/blob/master/README.md#how-to-use))

## iPhone 环境准备

如果你使用的是 iPhone 设备，请参考专门的 iOS 配置文档：

📱 [iOS 环境配置指南](docs/ios_setup/ios_setup.md)

该文档详细介绍了如何配置 WebDriverAgent 以便于 iPhone 设备，以便在 iOS 上使用 AutoPhone。

## 部署准备工作

### 1. 安装依赖

```bash
pip install -r requirements.txt
pip install -e .
```

### 2. 配置 ADB 和 HDC

#### 对于 Android 设备

确认 **USB数据线具有数据传输功能**，而不是仅有充电功能。

确保已安装 ADB 并使用 **USB数据线** 连接设备后：

```bash
# 检查已连接的设备
adb devices

# 输出结果应显示你的设备，如：
# List of devices attached
# emulator-5554   device
```

#### 对于鸿蒙设备

确认 **USB数据线具有数据传输功能**，而不是仅有充电功能。

确保已安装 HDC 并使用 **USB数据线** 连接设备后：

```bash
# 检查已连接的设备
hdc list targets

# 输出结果应显示你的设备，如：
# 7001005458323933328a01bce01c2500
```

### 3. 启动模型服务

你可以选择自行部署模型服务，或使用第三方模型服务商。

#### 选项 A: 使用第三方模型服务

如果你不想自行部署模型，可以使用以下已部署我们模型的第三方服务：

**1. 智谱 BigModel**

- 文档: https://docs.bigmodel.cn/cn/api/introduction
- `--base-url`: `https://open.bigmodel.cn/api/paas/v4`
- `--model`: `AutoPhone-phone`
- `--apikey`: 在智谱平台申请你的 API Key

**2. ModelScope(魔搭社区)**

- 文档: https://modelscope.cn/models/ZhipuAI/AutoPhone-Phone-9B
- `--base-url`: `https://api-inference.modelscope.cn/v1`
- `--model`: `ZhipuAI/AutoPhone-Phone-9B`
- `--apikey`: 在 ModelScope 平台申请你的 API Key

使用第三方服务的示例：

```bash
# 使用智谱 BigModel
python main.py --base-url https://open.bigmodel.cn/api/paas/v4 --model "AutoPhone-phone" --apikey "your-bigmodel-api-key" "打开美团搜索附近的火锅店"

# 使用 ModelScope
python main.py --base-url https://api-inference.modelscope.cn/v1 --model "ZhipuAI/AutoPhone-Phone-9B" --apikey "your-modelscope-api-key" "打开美团搜索附近的火锅店"
```

#### 选项 B: 自行部署模型

如果你希望在本地或自己的服务器上部署模型：

1. 按照 `requirements.txt` 中 `For Model Deployment` 章节自行安装推理引擎框架。

对于 SGLang：除了使用 pip 安装，你也可以使用官方 docker:

> ```shell
> docker pull lmsysorg/sglang:v0.5.6.post1
> ```
>
> 进入容器，执行：
>
> ```
> pip install nvidia-cudnn-cu12==9.16.0.29
> ```

对于 vLLM，除了使用 pip 安装，你也可以使用官方 docker:

> ```shell
> docker pull vllm/vllm-openai:v0.12.0
> ```
>
> 进入容器，执行：
>
> ```
> pip install -U transformers --pre
> ```

**注意**: 上述步骤出现的关于 transformers 的依赖冲突可以忽略。

1. 在对应容器或者实体机上（非容器安装）下载模型，通过 SGlang / vLLM 启动，获得 OpenAI 格式服务。这里提供一个 vLLM 部署方案，请严格遵循我们提供的启动参数：

- vLLM:

```shell
python3 -m vllm.entrypoints.openai.api_server \
 --served-model-name AutoPhone-phone-9b \
 --allowed-local-media-path /   \
 --mm-encoder-tp-mode data \
 --mm_processor_cache_type shm \
 --mm_processor_kwargs "{\"max_pixels\":5000000}" \
 --max-model-len 25480  \
 --chat-template-content-format string \
 --limit-mm-per-prompt "{\"image\":10}" \
 --model zai-org/AutoPhone-Phone-9B \
 --port 8000
```

- SGLang:

```shell
python3 -m sglang.launch_server --model-path  zai-org/AutoPhone-Phone-9B \
        --served-model-name AutoPhone-phone-9b  \
        --context-length 25480  \
        --mm-enable-dp-encoder   \
        --mm-process-config '{"image":{"max_pixels":5000000}}'  \
        --port 8000
```

- 该模型结构与 `GLM-4.1V-9B-Thinking` 相同, 关于模型部署的详细内容，你也可以查 [GLM-V](https://github.com/zai-org/GLM-V)
  获取模型部署和使用指南。

- 运行成功后，将可以通过 `http://localhost:8000/v1` 访问模型服务。如果您在远程服务器部署模型，使用该服务器的 IP 访问模型。

### 4. 检查模型部署

模型服务启动后，可以使用检查脚本验证部署是否成功：

```bash
python scripts/check_deployment_cn.py --base-url http://你的IP:你的端口/v1 --model 模型名称
```

脚本将发送测试请求并展示模型的推理结果，你可以根据输出判断模型部署是否正常工作。

基于给定的任务，预期输出如下。**如果思维链长度很短，或者出现了乱码，很可能是模型部署失败**，请仔细检查文档要求的配置和依赖：

```
<think>用户想要比较这个洗发水在京东和淘宝上的价格，然后选择最便宜的平台下单。当前在小红书app上，显示的是一个关于LUMMI MOOD洗发水的帖子？

我需要：
1. 先启动京东app，搜索这个洗发水
2. 查看京东的价格
3. 再启动淘宝app，搜索这个洗发水
4. 查看淘宝的价格
5. 比较价格后，选择最便宜的京东或淘宝下单

首先，我需要从当前的小红书界面退出，然后启动京东app？/think>
<answer>do(action="Launch", app="京东")
```

**参数说明：**
- `--base-url`: 模型服务地址(根据实际部署地址修改)
- `--model`: 模型名称
- `--messages-file`: 可选，指定自定义测试消息文件。默认使用 `scripts/sample_messages.json`)

## 使用 AutoPhone

### 命令行

根据你部署的模型, 设置 `--base-url` 和 `--model` 参数, 设置 `--device-type` 指定是安卓设备或鸿蒙设备 (默认是 adb 表示安卓设备, hdc 表示鸿蒙设备). 例如:

```bash
# Android 设备 - 交互模式
python main.py --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b"

# Android 设备 - 指定任务
python main.py --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 鸿蒙设备 - 交互模式
python main.py --device-type hdc --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b"

# 鸿蒙设备 - 指定任务
python main.py --device-type hdc --base-url http://localhost:8000/v1 "打开美团搜索附近的火锅店"

# 使用 API Key 进行认证
python main.py --apikey sk-xxxxx

# 使用英文 system prompt
python main.py --lang en --base-url http://localhost:8000/v1 "Open Chrome browser"

# 列出支持的应用（Android）
python main.py --list-apps

# 列出支持的应用（鸿蒙）
python main.py --device-type hdc --list-apps
```

### Python API

```python
from phone_agent import PhoneAgent
from phone_agent.model import ModelConfig

# Configure model
model_config = ModelConfig(
    base_url="http://localhost:8000/v1",
    model_name="AutoPhone-phone-9b",
)

# 创建 Agent
agent = PhoneAgent(model_config=model_config)

# 执行任务
result = agent.run("打开淘宝搜索无线耳机")
print(result)
```

## 远程调试

Phone Agent 支持通过 WiFi/网络进行远程 ADB/HDC 调试，无需 USB 连接即可控制设备。

### 配置远程调试

#### 在手机端开启无线调试

##### Android 设备

确保手机和电脑在同一个WiFi中，如图所示：

![开启无线调试](resources/setting.png)

##### 鸿蒙设备

确保手机和电脑在同一个WiFi中：
1. 进入 `设置 > 系统和更新 > 开发者选项`
2. 打开 `USB 调试` 和 `无线调试`
3. 记录显示的 IP 地址和端口号

#### 在电脑端使用标准 ADB/HDC 命令

```bash
# Android 设备 - 通过 WiFi 连接, 改成手机显示的 IP 地址和端口
adb connect 192.168.1.100:5555

# 验证连接
adb devices
# 应显示：192.168.1.100:5555    device

# 鸿蒙设备 - 通过 WiFi 连接
hdc tconn 192.168.1.100:5555

# 验证连接
hdc list targets
# 应显示：192.168.1.100:5555
```

### 设备管理命令

#### Android 设备（ADB）

```bash
# 列出所有已连接设备
adb devices

# 连接远程设备
adb connect 192.168.1.100:5555

# 断开指定设备
adb disconnect 192.168.1.100:5555

# 指定设备执行任务
python main.py --device-id 192.168.1.100:5555 --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b" "打开抖音刷视频"
```

#### 鸿蒙设备（HDC）

```bash
# 列出所有已连接设备
hdc list targets

# 连接远程设备
hdc tconn 192.168.1.100:5555

# 断开指定设备
hdc tdisconn 192.168.1.100:5555

# 指定设备执行任务
python main.py --device-type hdc --device-id 192.168.1.100:5555 --base-url http://localhost:8000/v1 --model "AutoPhone-phone-9b" "打开抖音刷视频"
```

### Python API 远程连接

#### Android 设备（ADB）

```python
from phone_agent.adb import ADBConnection, list_devices

# 创建连接管理：
conn = ADBConnection()

# 连接远程设备
success, message = conn.connect("192.168.1.100:5555")
print(f"连接状态: {message}")

# 列出已连接设备：
devices = list_devices()
for device in devices:
    print(f"{device.device_id} - {device.connection_type.value}")

# 在 USB 设备上启用 TCP/IP
success, message = conn.enable_tcpip(5555)
ip = conn.get_device_ip()
print(f"设备 IP: {ip}")

# 断开连接
conn.disconnect("192.168.1.100:5555")
```

#### 鸿蒙设备（HDC）

```python
from phone_agent.hdc import HDCConnection, list_devices

# 创建连接管理：
conn = HDCConnection()

# 连接远程设备
success, message = conn.connect("192.168.1.100:5555")
print(f"连接状态: {message}")

# 列出已连接设备：
devices = list_devices()
for device in devices:
    print(f"{device.device_id} - {device.connection_type.value}")

# 断开连接
conn.disconnect("192.168.1.100:5555")
```

### 远程连接问题排查

**连接被拒绝：**

- 确保设备和电脑在同一网络
- 检查防火墙是否阻止 5555 端口
- 确认已启用 TCP/IP 模式：`adb tcpip 5555`

**连接断开：**

- WiFi 可能断开了，使用 `--connect` 重新连接
- 部分设备重启后会禁用 TCP/IP，需要通过 USB 重新启用

**多设备：**

- 使用 `--device-id` 指定要使用的设备
- 或使用 `--list-devices` 查看所有已连接设备

## 配置

### 自定义 SYSTEM PROMPT

系统提供中英文两种 prompt，通过 `--lang` 参数切换。

- `--lang cn` - 中文 prompt(默认)，配置文件：`phone_agent/config/prompts_zh.py`
- `--lang en` - 英文 prompt，配置文件：`phone_agent/config/prompts_en.py`

可以直接修改对应的配置文件来增强模型在特定领域的能力，或通过注入 app 名称禁用某些 app。

### 环境变量

| 变量                          | 描述                     | 默认值                       |
|-----------------------------|------------------------|----------------------------|
| `PHONE_AGENT_BASE_URL`      | 模型 API 地址              | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL`         | 模型名称                   | `AutoPhone-phone-9b`         |
| `PHONE_AGENT_API_KEY`       | 模型认证 API Key           | `EMPTY`                    |
| `PHONE_AGENT_MAX_STEPS`     | 每个任务最大步数              | `100`                      |
| `PHONE_AGENT_DEVICE_ID`     | ADB/HDC 设备 ID          | (自动检测)                     |
| `PHONE_AGENT_DEVICE_TYPE`   | 设备类型 (`adb` 或 `hdc`)   | `adb`                      |
| `PHONE_AGENT_LANG`          | 语言 (`cn` 或 `en`)       | `cn`                       |

### 模型配置

```python
from phone_agent.model import ModelConfig

config = ModelConfig(
    base_url="http://localhost:8000/v1",
    api_key="EMPTY",  # API 密钥(如需)
    model_name="AutoPhone-phone-9b",  # 模型名称
    max_tokens=3000,  # 最大输出 token 数
    temperature=0.1,  # 采样温度
    frequency_penalty=0.2,  # 频率惩罚
)
```

### Agent 配置

```python
from phone_agent.agent import AgentConfig

config = AgentConfig(
    max_steps=100,  # 每个任务最大步数
    device_id=None,  # ADB 设备 ID(None 为自动检测)
    lang="cn",  # 语言选择：cn(中文)或 en(英文)
    verbose=True,  # 打印调试信息(包括思考过程和执行动作)
)
```

### Verbose 模式输出

当 `verbose=True` 时，Agent 会在每一步输出详细信息：

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

... (执行动作后继续下一步

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

这样可以清楚地看到 AI 的推理过程和每一步的具体操作。

## 支持的应用

### Android 应用

Phone Agent 支持 50+ 款主流中文应用：

| 分类   | 应用              |
|------|-----------------|
| 社交通讯 | 微信、QQ、微博       |
| 电商购物 | 淘宝、京东、拼多多       |
| 美食外卖 | 美团、饿了么、肯德基      |
| 出行旅游 | 携程、12306、滴滴出行  |
