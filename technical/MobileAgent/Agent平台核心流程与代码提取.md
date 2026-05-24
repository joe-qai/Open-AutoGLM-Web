# Agent 平台核心流程与代码提取

> 基于 Mobile-Agent-v3.5 核心思想，提取完整核心代码作为平台开发示例，通篇可读
>
> 来源：https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5

---

## 目录

1. [核心思想](#1-核心思想)
2. [完整文件一：设备控制 + VLM 工具集（utils.py）](#2-完整文件一设备控制--vlm-工具集utilspy)
3. [完整文件二：Agent 主循环（run_gui_owl_1_5_for_mobile.py）](#3-完整文件二agent-主循环run_gui_owl_1_5_for_mobilepy)
4. [完整文件三：包名映射（packages.py）](#4-完整文件三包名映射packagespy)
5. [平台构建：适配器 + ReAct 引擎](#5-平台构建适配器--react-引擎)
6. [平台构建：动作分发器 + MCP 集成](#6-平台构建动作分发器--mcp-集成)
7. [平台构建：轨迹录制 + 脚本生成](#7-平台构建轨迹录制--脚本生成)
8. [平台构建：最小可运行示例](#8-平台构建最小可运行示例)

---

## 1. 核心思想

Mobile-Agent-v3.5 的核心是一个**单 Agent ReAct 循环**：

```
for 每一步:
    1. 截图当前手机屏幕
    2. 将截图 + 指令 + 历史记录 发给 VLM（视觉语言模型）
    3. VLM 返回动作描述 + <tool_call> JSON
    4. 解析 JSON，提取动作类型和参数
    5. 通过 ADB 执行动作（点击/滑动/输入...）
    6. 记录历史，等 2 秒看结果
    7. 重复直到 terminate
```

三个核心文件构成了完整平台：

| 文件 | 路径 | 行数 | 职责 |
|------|------|------|------|
| `utils.py` | `mobile_use/utils.py` | 659 | 设备控制、VLM 调用、截图标注、消息构建、Prompt |
| `run_gui_owl_1_5_for_mobile.py` | `mobile_use/run_gui_owl_1_5_for_mobile.py` | 287 | ReAct 主循环、动作解析、坐标系变换 |
| `packages.py` | `mobile_use/packages.py` | 191 | Android 包名 ↔ 应用名 双向映射 |

以下按文件完整呈现所有代码，每段紧跟其设计意图说明。

---

## 2. 完整文件一：设备控制 + VLM 工具集（utils.py）

### 2.1 ADB 设备控制类（AdbTools）

```
class AdbTools:
    """Wrapper around ADB commands for device interaction."""

    def __init__(self, adb_path, device=None):
        self.adb_path = adb_path
        self.device = device
        self._device_flag = f" -s {device} " if device is not None else " "
        self.image_info = None
```

**设计意图**：接收 ADB 路径和设备序列号，构造 `_device_flag`。这是平台抽象层的基础——未来 iOS/鸿蒙适配器只需替换 `_run()` 的实现。

```
    def _run(self, args):
        """Run an ADB command string."""
        cmd = self.adb_path + self._device_flag + args
        subprocess.run(cmd, capture_output=True, text=True, shell=True)
```

**设计意图**：所有 ADB 操作的单一入口点。截获此方法即可实现日志、重试、Mock 测试。

```
    def _load_image_info(self, path):
        """Cache the width and height of the screenshot."""
        width, height = Image.open(path).size
        self.image_info = (width, height)
```

```
    def get_screenshot(self, image_path, retry_times=3):
        device_flag = f" -s {self.device}" if self.device else ""
        cmd = f"{self.adb_path}{device_flag} exec-out screencap -p > {image_path}"
        for _ in range(retry_times):
            subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if os.path.exists(image_path):
                self._load_image_info(image_path)
                return True
            time.sleep(0.1)
        return False
```

**设计意图**：截图是 ReAct 循环的"眼睛"，重试机制保证即使偶发失败也能继续。

```
    def click(self, x, y):
        """Tap at screen coordinate (x, y)."""
        self._run(f"shell input tap {x} {y}")

    def long_press(self, x, y, duration=800):
        """Long-press at (x, y) for *duration* milliseconds."""
        self._run(f"shell input swipe {x} {y} {x} {y} {duration}")

    def slide(self, x1, y1, x2, y2, slide_time=800):
        """Swipe from (x1, y1) to (x2, y2) over *slide_time* milliseconds."""
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {slide_time}")
```

**设计意图**：四个核心交互动作，全部使用原始像素坐标。后续平台改进中，这些方法会被元素定位器（根据 resource_id/text 找坐标）替代。

```
    def back(self):
        """Press the Back button."""
        self._run("shell input keyevent 4")

    def home(self):
        """Press the Home button to return to the home screen."""
        self._run("shell am start -a android.intent.action.MAIN "
                   "-c android.intent.category.HOME")
```

```
    def type(self, text):
        """
        Type text via ADB Keyboard (supports CJK and Latin characters).
        Requires ADB Keyboard to be installed on the device.
        """
        escaped_text = text.replace('"', '\\"').replace("'", "\\'")
        command_sequence = [
            "shell ime enable com.android.adbkeyboard/.AdbIME",
            "shell ime set com.android.adbkeyboard/.AdbIME",
            0.1,
            f'shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped_text}"',
            0.1,
            "shell ime disable com.android.adbkeyboard/.AdbIME",
        ]
        for item in command_sequence:
            if isinstance(item, (int, float)):
                time.sleep(item)
            else:
                self._run(item.strip())
```

**设计意图**：输入中文需要切换输入法为 ADB Keyboard，这是 Android 端最复杂的操作。iOS 和鸿蒙的实现方式完全不同，适配器模式在此体现价值。

```
    def get_package_name(self, all_packages=False):
        try:
            flag = "" if all_packages else " -3"
            cmd = f"{self.adb_path}{self._device_flag}shell pm list packages{flag}"
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            pkgs = []
            for line in res.stdout.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("package:"):
                    s = s[len("package:"):]
                if "=" in s:
                    _, s = s.split("=", 1)
                if s:
                    pkgs.append(s)
            return sorted(set(pkgs))
        except Exception as e:
            print(f"[ERROR] Failed to list packages: {e}")
            return []

    def open_app(self, package_name):
        """Launch an app by its package name."""
        self._run(f"shell monkey -p {package_name} "
                  "-c android.intent.category.LAUNCHER 1")
```

### 2.2 截图标注

```
def annotate_screenshot(image_path, action_parameter, save_path="screenshot_anno.png"):
    """Draw action annotations (click dot / swipe arrow) on a screenshot."""
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    action_type = action_parameter.get("action", "")

    if action_type == "click":
        radius = 15
        cx, cy = action_parameter["coordinate"]
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     fill="red", outline="red")
    elif action_type in ("scroll", "swipe"):
        x1, y1 = action_parameter["coordinate"]
        x2, y2 = action_parameter["coordinate2"]
        draw.line((x1, y1, x2, y2), fill="red", width=2)
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10
        ax1 = x2 - arrow_size * math.cos(angle - math.pi / 6)
        ay1 = y2 - arrow_size * math.sin(angle - math.pi / 6)
        ax2 = x2 - arrow_size * math.cos(angle + math.pi / 6)
        ay2 = y2 - arrow_size * math.sin(angle + math.pi / 6)
        draw.polygon([(x2, y2), (ax1, ay1), (ax2, ay2)], fill=color)
    else:
        return None
    image.save(save_path)
    return save_path
```

**设计意图**：在截图上画红点和箭头，便于人眼追踪 Agent 每一步做了什么，是调试和展示的关键工具。

### 2.3 VLM 截图缩放（smart_resize）

```
def smart_resize(height, width, factor=16, min_pixels=None, max_pixels=None):
    IMAGE_MIN_TOKEN_NUM = 4
    IMAGE_MAX_TOKEN_NUM = 16384
    MAX_RATIO = 200
    max_pixels = max_pixels if max_pixels is not None else (IMAGE_MAX_TOKEN_NUM * factor ** 2)
    min_pixels = min_pixels if min_pixels is not None else (IMAGE_MIN_TOKEN_NUM * factor ** 2)
    assert max_pixels >= min_pixels, "max_pixels must be >= min_pixels."

    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(f"Aspect ratio must be < {MAX_RATIO}")

    def _round(n): return round(n / factor) * factor
    def _floor(n): return math.floor(n / factor) * factor
    def _ceil(n):  return math.ceil(n / factor) * factor

    h_bar = max(factor, _round(height))
    w_bar = max(factor, _round(width))

    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = _floor(height / beta)
        w_bar = _floor(width / beta)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = _ceil(height * beta)
        w_bar = _ceil(width * beta)

    return h_bar, w_bar
```

**设计意图**：Qwen-VL 的缩放算法，保证缩放后长宽都是 16 的倍数，且像素数在 VLM 可接受的范围内。

### 2.4 System Prompt（工具注册）

```
SYSTEM_PROMPT = '''# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{"type": "function", "function": {"name_for_human": "mobile_use",
  "name": "mobile_use",
  "description": "Use a touchscreen to interact with a mobile device, ...",
  "parameters": {"properties": {
    "action": {"enum": ["key", "click", "long_press", "swipe", "type",
                        "system_button", "open", "wait", "answer",
                        "interact", "terminate"], "type": "string"},
    "coordinate": {"type": "array"},
    "coordinate2": {"type": "array"},
    "text": {"type": "string"},
    "time": {"type": "number"},
    "button": {"enum": ["Back", "Home", "Menu", "Enter"], "type": "string"},
    "status": {"enum": ["success", "failure"], "type": "string"}
  }, "required": ["action"], "type": "object"},
  "args_format": "Format the arguments as a JSON object."}}
</tools>

For each function call, return ... within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>

Response format for every step:
1) Action: a short imperative describing what to do in the UI.
2) A single <tool_call>...</tool_call> block.

Rules:
- Output exactly in the order: Action, <tool_call>.
- Be brief: one for Action.
- Do not output anything else outside those two parts.
- If finishing, use action=terminate in the tool call.'''
```

**设计意图**：这是 Mobile-Agent 最核心的 Prompt 设计——通过 XML `<tools>` 包裹 JSON Schema 向 LLM 注册工具。LLM 在 `Action:` 后用自然语言描述意图，在 `<tool_call>` 中输出结构化的 JSON 参数。这种"自然语言 + 结构化"的双通道输出比纯 JSON 更稳定。

### 2.5 VLM 消息构建（build_messages）

```
def build_messages(image_path, instruction, history_output, model_name, history_n=4):
    """
    Construct the multi-turn message list for the VLM.
    Only the last `history_n` steps keep full images;
    earlier steps are summarized as text.
    """
    current_step = len(history_output)
    history_start_idx = max(0, current_step - history_n)

    # Summarize early actions as text-only descriptions
    previous_actions = []
    for i in range(history_start_idx):
        if i < len(history_output):
            text = history_output[i]["output"]
            if model_name.endswith(".mem"):
                if "<tool_call>" in text:
                    text = text.split("<tool_call>")[0].strip()
            else:
                if "Action:" in text and "<tool_call>" in text:
                    text = text.split("Action:")[1].split("<tool_call>")[0].strip()
            previous_actions.append(f"Step {i + 1}: {text}")

    previous_actions_str = "\n".join(previous_actions) if previous_actions else "None"

    today = datetime.today()
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
    formatted_date = today.strftime("%Y-%m-%d") + " " + weekday_names[today.weekday()]
    date_info = f"Today's date is: {formatted_date}."

    instruction_prompt = (
        f"Please generate the next move according to the UI screenshot, "
        f"instruction and previous actions.\n\n"
        f"Instruction: {date_info}{instruction}\n\n"
        f"Previous actions:\n{previous_actions_str}"
    )

    messages = [{"role": "system", "content": [{"text": SYSTEM_PROMPT}]}]

    history_len = min(history_n, len(history_output))
    if history_len > 0:
        for idx, item in enumerate(history_output[-history_n:]):
            if idx == 0:
                messages.append({
                    "role": "user",
                    "content": [{"text": instruction_prompt},
                                {"image": "file://" + item["image"]}],
                })
            else:
                messages.append({
                    "role": "user",
                    "content": [{"image": "file://" + item["image"]}],
                })
            messages.append({
                "role": "assistant",
                "content": [{"text": item["output"]}],
            })
        messages.append({
            "role": "user",
            "content": [{"image": "file://" + image_path}],
        })
    else:
        messages.append({
            "role": "user",
            "content": [{"text": instruction_prompt},
                        {"image": "file://" + image_path}],
        })

    return messages
```

**设计意图**：关键设计是**滑动窗口 history**——截图为 token 大头，只保留最近 N 步的完整截图，更早的步骤用文字摘要代替。这是控制上下文长度的核心策略。

### 2.6 VLM 调用封装（GUIOwlWrapper）

```
class LlmWrapper(abc.ABC):
    """Abstract interface for text-only LLM."""
    @abc.abstractmethod
    def predict(self, text_prompt: str) -> tuple[str, Optional[bool], Any]: ...

class MultimodalLlmWrapper(abc.ABC):
    """Abstract interface for Multimodal LLM."""
    @abc.abstractmethod
    def predict_mm(self, text_prompt: str, images: list[np.ndarray]) -> tuple[str, Optional[bool], Any]: ...

class GUIOwlWrapper(LlmWrapper, MultimodalLlmWrapper):

    RETRY_WAITING_SECONDS = 20

    def __init__(self, api_key: str, base_url: str, model_name: str,
                 max_retry: int = 10, temperature: float = 0.0):
        if max_retry <= 0:
            max_retry = 10
        self.max_retry = min(max_retry, 10)
        self.temperature = temperature
        self.model = model_name
        self.bot = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
```

```
    def convert_messages_format_to_openaiurl(self, messages):
        """Convert internal message format to OpenAI API format."""
        converted_messages = []
        for message in messages:
            new_content = []
            for item in message['content']:
                if list(item.keys())[0] == 'text':
                    new_content.append({'type': 'text', 'text': item['text']})
                elif list(item.keys())[0] == 'image':
                    new_content.append({
                        'type': 'image_url',
                        'image_url': {'url': image_to_base64(item['image'])}
                    })
            converted_messages.append({'role': message['role'], 'content': new_content})
        return converted_messages
```

```
    def predict_mm(self, messages=None) -> tuple[str, Optional[bool], Any]:
        payload = messages
        payload = self.convert_messages_format_to_openaiurl(payload)

        counter = self.max_retry
        wait_seconds = self.RETRY_WAITING_SECONDS
        while counter > 0:
            try:
                chat_completion_from_url = self.bot.chat.completions.create(
                    model=self.model, messages=payload, **{})
                return (chat_completion_from_url.choices[0].message.content,
                        payload, chat_completion_from_url)
            except Exception as e:
                time.sleep(wait_seconds)
                counter -= 1
                print('Error calling LLM, will retry soon...')
                print(e)
        return 'Error calling LLM', None, None
```

### 2.7 应用名解析器

```
def resolve_app_name_via_llm(instruction, app_name_list_str, api_key,
                              base_url, model="qwen-plus"):
    prompt = f'''Role and Task:
You are an app resolver. Given a natural language instruction and a list of
installed app names on a device, determine which app needs to be opened.

Input:
User instruction: "{instruction}"
Installed apps: "{app_name_list_str}"

Rules:
- Only select from the given app name list; never fabricate names.
- If the instruction explicitly names an app and it exists, return its name.
- If not, return an empty string.

Output format (important):
Only output JSON, no extra text.
{{"reason": "...", "app": "..."}}
'''
    client = OpenAI(api_key=api_key, base_url=base_url)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    res_text = completion.choices[0].message.content
    print(f"[APP RESOLVER] LLM response: {res_text}")
    parsed = _try_parse_json(res_text)
    if parsed and "app" in parsed:
        return parsed["app"]
    return ""


def _try_parse_json(text):
    """Attempt to parse a JSON object from text, handling markdown fences."""
    if not text:
        return None
    try:
        cleaned = text
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        return json.loads(cleaned)
    except Exception as e:
        print(f"[WARN] JSON parse failed: {e}")
        return None
```

---

## 3. 完整文件二：Agent 主循环（run_gui_owl_1_5_for_mobile.py）

### 3.1 命令行入口与参数解析

```
import argparse
import json
import os
import shutil
import time
from PIL import Image
from packages import PACKAGES_NAME_DICT, NAME_PACKAGE_DICT
from utils import (
    AdbTools, annotate_screenshot, build_messages,
    resolve_app_name_via_llm, smart_resize, GUIOwlWrapper
)

def parse_args():
    parser = argparse.ArgumentParser(description="Mobile-Agent-v3.5")
    parser.add_argument("--adb_path", type=str, required=True,
                        help="Path to the ADB binary.")
    parser.add_argument("--device", type=str, default=None,
                        help="ADB device serial (optional, for multi-device).")
    parser.add_argument("--api_key", type=str, required=True,
                        help="API key for the VLM service.")
    parser.add_argument("--base_url", type=str, required=True,
                        help="Base URL for the VLM service.")
    parser.add_argument("--model", type=str, required=True,
                        help="Model name for the VLM service.")
    parser.add_argument("--instruction", type=str, required=True,
                        help="Task instruction for the agent.")
    parser.add_argument("--add_info", type=str, default="",
                        help="Supplementary knowledge (can be empty).")
    parser.add_argument("--max_steps", type=int, default=50,
                        help="Maximum number of interaction steps.")
    parser.add_argument("--app_resolver_api_key", type=str, default=None)
    parser.add_argument("--app_resolver_base_url", type=str, default=None)
    parser.add_argument("--app_resolver_model", type=str, default="qwen-plus")
    return parser.parse_args()
```

### 3.2 动作解析

```
def parse_action(output_text):
    """
    Extract the action dict from the model's output text.
    Expects a <tool_call> block containing JSON with nested 'arguments'.
    """
    try:
        tool_call_block = output_text.split("<tool_call>\n")[1]
        json_str = tool_call_block.split("}}\n")[0] + "}}"
        return json.loads(json_str)
    except (IndexError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse action from model output: {e}")
```

**设计意图**：从 `<tool_call>\n{"name":"mobile_use","arguments":{"action":"click","coordinate":[500,300]}}\n</tool_call>` 中提取 JSON。注意 `}}` 的匹配——`json_str.split("}}\n")[0] + "}}"` 取到 arguments 对象的结尾。

### 3.3 坐标系变换

```
def rescale_coordinates(action_parameter, resized_width, resized_height):
    """
    Convert normalized (0-1000) coordinates to actual pixel coordinates
    based on the resized image dimensions.
    """
    for key in ("coordinate", "coordinate1", "coordinate2"):
        if key in action_parameter:
            action_parameter[key][0] = int(
                action_parameter[key][0] / 1000 * resized_width
            )
            action_parameter[key][1] = int(
                action_parameter[key][1] / 1000 * resized_height
            )
    return action_parameter
```

**设计意图**：VLM 看到的是 1000x1000 的归一化图像，输出的坐标也是 0-1000 范围。此函数将 LLM 坐标映射到实际截图分辨率。这是跨分辨率适配的关键一环。

### 3.4 打开应用处理器

```
def handle_open_action(action_parameter, instruction, adb_tools,
                       resolver_api_key, resolver_base_url, resolver_model):
    app_name = action_parameter.get("text", "")
    package_candidates = NAME_PACKAGE_DICT.get(app_name, [])
    installed_packages = adb_tools.get_package_name()
    display_name = app_name

    # First attempt: direct lookup
    for pkg in package_candidates:
        if pkg in installed_packages:
            adb_tools.open_app(pkg)
            return True

    # Second attempt: resolve via LLM
    installed_app_names = []
    for pkg in installed_packages:
        if pkg in PACKAGES_NAME_DICT:
            installed_app_names.append(PACKAGES_NAME_DICT[pkg][0])

    resolved_name = resolve_app_name_via_llm(
        instruction, ", ".join(installed_app_names),
        api_key=resolver_api_key, base_url=resolver_base_url,
        model=resolver_model,
    )
    if resolved_name:
        display_name = resolved_name

    resolved_packages = NAME_PACKAGE_DICT.get(resolved_name, [])
    for pkg in resolved_packages:
        if pkg in installed_packages:
            adb_tools.open_app(pkg)
            return True

    input(f"[ACTION REQUIRED] Please install the app: {display_name}")
    return False
```

**设计意图**：先查包名映射字典直接匹配，失败后用 LLM 做语义解析（"打开微信"→"WeChat"→"com.tencent.mm"），最后才请求人工介入。

### 3.5 ReAct 主循环（核心）

```
def main():
    args = parse_args()
    adb_tools = AdbTools(adb_path=args.adb_path, device=args.device)

    instruction = args.instruction
    if args.add_info:
        instruction = f"{instruction} ({args.add_info})"

    task_dir = instruction.replace(" ", "_")[:80]
    anno_dir = task_dir + "_anno"

    for d in (task_dir, anno_dir):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d)

    resolver_api_key = args.app_resolver_api_key or args.api_key
    resolver_base_url = args.app_resolver_base_url or args.base_url
    resolver_model = args.app_resolver_model

    history = []

    for step_id in range(args.max_steps):
        print(f"\n{'='*50}")
        print(f"STEP {step_id}")
        print(f"{'='*50}")

        # 1. Capture screenshot
        screenshot_path = os.path.join(task_dir, f"screenshot_{step_id}.png")
        if not adb_tools.get_screenshot(screenshot_path):
            print("[ERROR] Failed to capture screenshot. Retrying...")
            time.sleep(1)
            continue

        # 2. Build messages and call the VLM
        messages = build_messages(
            screenshot_path, instruction, history, args.model
        )
        vllm = GUIOwlWrapper(args.api_key, args.base_url, args.model)
        output_text, _, _ = vllm.predict_mm(messages)
        print(f"[MODEL OUTPUT]\n{output_text}")

        # 3. Parse the action
        action = parse_action(output_text)
        action_parameter = action["arguments"]

        # 4. Rescale coordinates
        img = Image.open(screenshot_path)
        resized_h, resized_w = smart_resize(
            img.height, img.width, factor=16,
            min_pixels=3136, max_pixels=1003520 * 200,
        )
        action_parameter = rescale_coordinates(action_parameter, resized_w, resized_h)

        # 5. Execute the action
        action_type = action_parameter["action"]

        if action_type == "click":
            adb_tools.click(
                action_parameter["coordinate"][0],
                action_parameter["coordinate"][1],
            )
        elif action_type == "long_press":
            adb_tools.long_press(
                action_parameter["coordinate"][0],
                action_parameter["coordinate"][1],
            )
        elif action_type == "type":
            adb_tools.type(action_parameter["text"])
        elif action_type in ("scroll", "swipe"):
            adb_tools.slide(
                action_parameter["coordinate"][0],
                action_parameter["coordinate"][1],
                action_parameter["coordinate2"][0],
                action_parameter["coordinate2"][1],
            )
        elif action_type == "system_button":
            button = action_parameter["button"]
            if button == "Back":
                adb_tools.back()
            elif button == "Home":
                adb_tools.home()
        elif action_type == "wait":
            wait_time = action_parameter.get("time", 2)
            time.sleep(wait_time)
        elif action_type == "terminate":
            status = action_parameter.get("status", "unknown")
            print(f"[TERMINATED] Status: {status}")
            break
        elif action_type == "open":
            opened = handle_open_action(
                action_parameter, instruction, adb_tools,
                resolver_api_key, resolver_base_url, resolver_model,
            )
            if not opened:
                continue
        elif action_type == "answer":
            conclusion = output_text.split("<tool_call>")[0].strip()
            print(f"[ANSWER] {conclusion}")
            print("[TERMINATED] Task completed.")
            break
        elif action_type in ("call_user", "calluser", "interact"):
            user_prompt = action_parameter.get("text", "the required action")
            input(f"[ACTION REQUIRED] Please complete: {user_prompt}")
            print("[INFO] User action completed. Resuming...")
        else:
            print(f"[WARN] Unsupported action type: {action_type}")

        # 6. Record history and annotate screenshot
        history.append({"output": output_text, "image": screenshot_path})
        annotate_screenshot(
            screenshot_path, action_parameter,
            os.path.join(anno_dir, f"screenshot_anno_{step_id}.png"),
        )
        time.sleep(2)

    print("\n[DONE] Agent execution finished.")


if __name__ == "__main__":
    main()
```

---

## 4. 完整文件三：包名映射（packages.py）

```
"""
Package name mapping between Android package identifiers and human-readable app names.
Provides bidirectional lookup: package -> names and name -> packages.
"""

PACKAGE_STR_LIST = '''com.tencent.mm	微信	wechat
com.tencent.mobileqq	qq	腾讯qq
com.sina.weibo	微博
com.taobao.taobao	淘宝
com.jingdong.app.mall	京东	京东秒送
com.xunmeng.pinduoduo	拼多多
com.xingin.xhs	小红书
com.douban.frodo	豆瓣
com.zhihu.android	知乎
com.autonavi.minimap	高德地图	高德
com.baidu.BaiduMap	百度地图
com.sankuai.meituan.takeoutnew	美团外卖
com.sankuai.meituan	美团	美团外卖
com.dianping.v1	大众点评	点评
me.ele	饿了么	淘宝闪购
com.yek.android.kfc.activitys	肯德基
ctrip.android.view	携程	携程旅行
com.MobileTicket	铁路12306	12306
com.Qunar	去哪儿旅行	去哪儿网	去哪儿
com.sdu.didi.psnger	滴滴出行	滴滴
tv.danmaku.bili	bilibili	b站	哔哩哔哩	哔站	bili
com.ss.android.ugc.aweme	抖音
com.smile.gifmaker	快手
com.tencent.qqlive	腾讯视频
com.qiyi.video	爱奇艺
com.youku.phone	优酷	优酷视频
com.hunantv.imgo.activity	芒果tv	芒果
com.phoenix.read	红果短剧	红果
com.netease.cloudmusic	网易云音乐	网易云
com.tencent.qqmusic	qq音乐
com.luna.music	汽水音乐
com.ximalaya.ting.android	喜马拉雅
com.dragon.read	番茄免费小说	番茄小说
com.kmxs.reader	七猫免费小说
com.ss.android.lark	飞书
com.tencent.androidqqmail	qq邮箱
com.larus.nova	豆包	豆包
com.gotokeep.keep	keep
com.lingan.seeyou	美柚
com.tencent.news	腾讯新闻
com.ss.android.article.news	今日头条
com.lianjia.beike	贝壳找房
com.anjuke.android.app	安居客
com.hexin.plat.android	同花顺
com.miHoYo.hkrpg	星穹铁道	崩坏
com.papegames.lysk.cn	恋与深空
com.android.settings	settings	androidsystemsettings
com.android.soundrecorder	audiorecorder
com.rammigsoftware.bluecoins	bluecoins
com.flauschcode.broccoli	broccoli
com.booking	booking
com.android.chrome	谷歌浏览器	googlechrome	chrome
com.android.deskclock	时钟	闹钟	clock
com.android.contacts	contacts
com.duolingo	duolingo	多邻国
com.expedia.bookings	expedia
com.android.fileexplorer	files	filemanager
com.google.android.gm	gmail	googlemail
com.google.android.apps.nbu.files	googlefiles	filesbygoogle
com.google.android.calendar	googlecalendar
com.google.android.apps.dynamite	googlechat
com.google.android.deskclock	googleclock
com.google.android.contacts	googlecontacts
com.google.android.apps.docs.editors.docs	googledocs
com.google.android.apps.docs	googledrive
com.google.android.apps.fitness	googlefit
com.google.android.keep	googlekeep
com.google.android.apps.maps	googlemaps
com.google.android.apps.books	googleplaybooks
com.android.vending	googleplaystore
com.google.android.apps.docs.editors.slides	googleslides
com.google.android.apps.tasks	googletasks
net.cozic.joplin	joplin
com.mcdonalds.app	麦当劳	mcdonald
net.osmand	osmand
com.Project100Pi.themusicplayer	pimusicplayer
com.quora.android	quora
com.reddit.frontpage	reddit
code.name.monkey.retromusic	retromusic
com.scientificcalculatorplus.simplecalculator.basiccalculator.mathcalc	simplecalendarpro
com.simplemobiletools.smsmessenger	simplesmsmessenger
org.telegram.messenger	telegram
com.einnovation.temu	temu
com.zhiliaoapp.musically	tiktok
com.twitter.android	twitter	x
org.videolan.vlc	vlc
com.whatsapp	whatsapp
com.taobao.movie.android	淘票票
com.tongcheng.android	同程旅行	同程
com.sankuai.movie	猫眼
com.wuba.zhuanzhuan	转转
com.tencent.weread	微信读书
com.taobao.idlefish	闲鱼
com.wudaokou.hippo	盒马
com.eg.android.AlipayGphone	支付宝
com.jd.jrapp	京东金融
com.achievo.vipshop	唯品会
com.smzdm.client.android	什么值得买
cn.kuwo.player	酷我音乐
com.taobao.trip	飞猪	飞猪旅行
com.jingdong.pdj	京东到家
com.tencent.map	腾讯地图
com.shizhuang.duapp	得物
cn.damai	大麦	大麦网
com.ss.android.auto	懂车帝
com.cubic.autohome	汽车之家
com.wuba	58同城	五八同城
com.android.calendar	日历
com.alibaba.android.rimet	钉钉
com.meituan.retail.v.android	小象超市
com.aliyun.tongyi	通义	千问	通义千问
com.hupu.games	虎扑	虎扑体育
com.quark.browser	夸克	夸克浏览器
com.yuantiku.tutor	猿辅导
com.tencent.mtt	qq浏览器
com.umetrip.android.msky.app	航旅纵横
com.UCMobile	UC浏览器
com.ss.android.ugc.aweme.lite	抖音极速版	抖音
air.tv.douyu.android	斗鱼
com.tencent.hunyuan.app.chat	元宝
com.baidu.searchbox	百度
com.lemon.lv	剪映
cn.soulapp.android	soul
com.baidu.netdisk	百度网盘
com.tmri.app.main	交管12123	12123
com.kugou.android	酷狗	酷狗音乐
com.ss.android.lark	飞书
com.tencent.android.qqdownloader	应用宝
com.mt.mtxx.mtxx	美图	美图秀秀
com.tencent.karaoke	全民k歌
com.intsig.camscanner	扫描全能王
com.android.bankabc	农业银行	农行
cmb.pb	招商银行	招行
com.ganji.android.haoche_c	瓜子二手车	瓜子
com.sf.activity	顺丰	顺丰快递	顺丰速运
com.ziroom.ziroomcustomer	自如
com.yumc.phsuperapp	必胜客
cn.dominos.pizza	达美乐披萨	达美乐
cn.wps.moffice_eng	WPS Office	WPS
com.mfw.roadbook	马蜂窝
com.moonshot.kimichat	kimi
com.tencent.wemeet.app	腾讯会议
com.deepseek.chat	deepseek
com.spdbccc.app	浦发银行
cn.samsclub.app	山姆超市	山姆	山姆会员商店	山姆会员店
com.tencent.qqsports	腾讯体育
com.hanweb.android.zhejiang.activity	浙里办
com.ss.android.article.video	西瓜视频
com.taou.maimai	脉脉'''

def normalize_package_name(name):
    """Normalize an app name by converting to lowercase and removing spaces/hyphens."""
    return name.lower().strip().replace(" ", "").replace("-", "")

def build_package_dicts():
    """Build bidirectional lookup dictionaries from the package string list."""
    packages_name_dict = {}
    name_package_dict = {}
    for line in PACKAGE_STR_LIST.strip().split("\n"):
        parts = line.strip().split("\t")
        if not parts:
            continue
        package_id = parts[0]
        names = [normalize_package_name(n) for n in parts[1:] if n.strip()]
        packages_name_dict[package_id] = names
        for name in names:
            if name not in name_package_dict:
                name_package_dict[name] = [package_id]
            else:
                name_package_dict[name].append(package_id)
    return packages_name_dict, name_package_dict

PACKAGES_NAME_DICT, NAME_PACKAGE_DICT = build_package_dicts()
```

---

## 5. 平台构建：适配器 + ReAct 引擎

从以上三个文件提取核心代码后，可以构建更工程化的平台。以下代码不引用原始文件，而是独立的完整实现。

### 5.1 设备适配器抽象层

```
from abc import ABC, abstractmethod
import subprocess
import time
import os
from PIL import Image


class BaseDeviceAdapter(ABC):
    """所有平台的统一接口——替换 AdbTools 的硬编码依赖"""

    @abstractmethod
    def screenshot(self, path: str) -> bool: ...

    @abstractmethod
    def click(self, x: int, y: int): ...

    @abstractmethod
    def type(self, text: str): ...

    @abstractmethod
    def open_app(self, app_id: str): ...

    @abstractmethod
    def press_back(self): ...

    @abstractmethod
    def press_home(self): ...

    @abstractmethod
    def swipe(self, x1: int, y1: int, x2: int, y2: int): ...


class AndroidAdapter(BaseDeviceAdapter):
    """复用 AdbTools 核心逻辑"""

    def __init__(self, adb_path: str, device_serial: str = None):
        self._adb_path = adb_path
        self._flag = f" -s {device_serial} " if device_serial else " "

    def _run(self, cmd: str):
        subprocess.run(self._adb_path + self._flag + cmd,
                       capture_output=True, shell=True)

    def screenshot(self, path: str) -> bool:
        flag = f" -s {self._device}" if hasattr(self, '_device') else ""
        cmd = f"{self._adb_path}{flag} exec-out screencap -p > {path}"
        subprocess.run(cmd, capture_output=True, shell=True)
        return os.path.exists(path)

    def click(self, x: int, y: int):
        self._run(f"shell input tap {x} {y}")

    def type(self, text: str):
        escaped = text.replace('"', '\\"').replace("'", "\\'")
        self._run("shell ime enable com.android.adbkeyboard/.AdbIME")
        self._run("shell ime set com.android.adbkeyboard/.AdbIME")
        time.sleep(0.1)
        self._run(f'shell am broadcast -a ADB_INPUT_TEXT --es msg "{escaped}"')
        time.sleep(0.1)
        self._run("shell ime disable com.android.adbkeyboard/.AdbIME")

    def open_app(self, app_id: str):
        self._run(f"shell monkey -p {app_id} -c android.intent.category.LAUNCHER 1")

    def press_back(self):
        self._run("shell input keyevent 4")

    def press_home(self):
        self._run("shell am start -a android.intent.action.MAIN -c android.intent.category.HOME")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: int = 800):
        self._run(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")


class iOSAdapter(BaseDeviceAdapter):
    """通过 facebook-wda 控制 iOS 设备"""

    def __init__(self, wda_url: str):
        import wda
        self._client = wda.Client(wda_url)

    def screenshot(self, path: str) -> bool:
        self._client.screenshot().save(path)
        return os.path.exists(path)

    def click(self, x: int, y: int):
        self._client.tap(x, y)

    def type(self, text: str):
        self._client(type="text").set_text(text)

    def open_app(self, app_id: str):
        self._client.session().app_activate(app_id)

    def press_back(self):
        self._client.press("home")  # iOS 无统一返回

    def press_home(self):
        self._client.press("home")

    def swipe(self, x1: int, y1: int, x2: int, y2: int):
        self._client.swipe(x1, y1, x2, y2)


class HarmonyOSAdapter(BaseDeviceAdapter):
    """通过 hdc 控制鸿蒙设备"""

    def __init__(self, hdc_path: str, serial: str = None):
        self._hdc = hdc_path
        self._flag = f" -t {serial} " if serial else " "

    def _run(self, cmd: str):
        subprocess.run(self._hdc + self._flag + cmd, capture_output=True, shell=True)

    def screenshot(self, path: str) -> bool:
        self._run(f"shell snapshot_display -f {path}")
        return os.path.exists(path)

    def click(self, x: int, y: int):
        self._run(f"shell input tap {x} {y}")

    def type(self, text: str):
        self._run(f'shell input text "{text}"')

    def open_app(self, app_id: str):
        self._run(f'shell aa start -a Ability -b {app_id}')

    def press_back(self):
        self._run("shell input keyevent 4")

    def press_home(self):
        self._run("shell input keyevent 3")

    def swipe(self, x1: int, y1: int, x2: int, y2: int):
        self._run(f"shell input swipe {x1} {y1} {x2} {y2}")


def create_device_adapter(platform: str, **kwargs) -> BaseDeviceAdapter:
    """工厂方法——根据平台名创建对应适配器"""
    if platform == "android":
        return AndroidAdapter(kwargs["adb_path"], kwargs.get("device_serial"))
    elif platform == "ios":
        return iOSAdapter(kwargs["wda_url"])
    elif platform == "harmonyos":
        return HarmonyOSAdapter(kwargs["hdc_path"], kwargs.get("serial"))
    raise ValueError(f"Unsupported platform: {platform}")
```

### 5.2 可复用 ReAct 引擎

```
import json
import time
from datetime import datetime
from openai import OpenAI


class VLMClient:
    """VLM 调用封装——从 GUIOwlWrapper 提取并简化"""

    def __init__(self, api_key: str, base_url: str, model: str, max_retry: int = 10):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
        self.model = model
        self.max_retry = max_retry

    def chat(self, messages: list) -> str:
        for attempt in range(self.max_retry):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model, messages=messages)
                return resp.choices[0].message.content
            except Exception as e:
                print(f"[VLM] Attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)
        raise RuntimeError("VLM call failed after all retries")


class MessageBuilder:
    """消息构建器——从 build_messages + SYSTEM_PROMPT 提取"""

    def __init__(self, tool_schemas: list[dict], history_window: int = 4):
        self.tool_schemas = tool_schemas
        self.window = history_window

    def build_system_prompt(self) -> str:
        lines = ["# Tools", ""]
        for schema in self.tool_schemas:
            lines.append(json.dumps(schema, indent=2))
        lines.append("""
For each function call, return JSON within <tool_call></tool_call> XML tags:
<tool_call>
{"name": "...", "arguments": {...}}
</tool_call>

Response format:
1) Action: a short imperative describing what to do.
2) A single <tool_call>...</tool_call> block.
""")
        return "\n".join(lines)

    def build(self, instruction: str, screenshot_path: str,
              history: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": self.build_system_prompt()}]

        # Recent history (image-level)
        for h in history[-self.window:]:
            messages.append({"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": h["image"]}}
            ]})
            messages.append({"role": "assistant", "content": h["output"]})

        # Current instruction + screenshot
        user_content = []
        if not history:
            user_content.append({"type": "text", "text": instruction})
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"file://{screenshot_path}"}
        })
        messages.append({"role": "user", "content": user_content})
        return messages


class ActionParser:
    """动作解析器——从 parse_action 提取"""

    @staticmethod
    def parse(text: str) -> dict:
        try:
            block = text.split("<tool_call>")[1].split("</tool_call>")[0]
            return json.loads(block.strip())
        except (IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to parse action: {e}")


class ReActEngine:
    """可复用的 ReAct 执行引擎"""

    def __init__(self, device: BaseDeviceAdapter, vlm: VLMClient,
                 msg_builder: MessageBuilder, max_steps: int = 50):
        self.device = device
        self.vlm = vlm
        self.msg_builder = msg_builder
        self.max_steps = max_steps
        self.history = []

    def run(self, instruction: str):
        for step in range(self.max_steps):
            print(f"\n{'='*50}")
            print(f"STEP {step}")
            print(f"{'='*50}")

            # 1. Screenshot
            screenshot = f"screenshot_{step}.png"
            if not self.device.screenshot(screenshot):
                print("[ERROR] Screenshot failed")
                continue

            # 2. VLM
            messages = self.msg_builder.build(instruction, screenshot, self.history)
            response = self.vlm.chat(messages)
            print(f"[VLM] {response[:200]}...")

            # 3. Parse
            action = ActionParser.parse(response)
            name = action.get("name", "")
            args = action.get("arguments", {})

            # 4. Execute
            self._execute(name, args)

            # 5. Record
            self.history.append({
                "step": step,
                "image": f"data:image/png;base64,{screenshot}",
                "output": response,
            })

            if name == "terminate":
                print("[DONE] Task completed")
                break

            time.sleep(2)

    def _execute(self, name: str, args: dict):
        """动作分发——直接路由到 device 适配器"""
        if name == "click":
            self.device.click(args.get("x", 0), args.get("y", 0))
        elif name == "type":
            self.device.type(args.get("text", ""))
        elif name == "open":
            self.device.open_app(args.get("app_id", ""))
        elif name == "press_back":
            self.device.press_back()
        elif name == "press_home":
            self.device.press_home()
        elif name == "swipe":
            self.device.swipe(args.get("x1", 0), args.get("y1", 0),
                              args.get("x2", 0), args.get("y2", 0))
        elif name == "wait":
            time.sleep(args.get("time", 2))
        elif name == "terminate":
            pass
        else:
            print(f"[WARN] Unknown action: {name}")
```

---

## 6. 平台构建：动作分发器 + MCP 集成

### 6.1 策略模式动作分发器

```
from abc import ABC, abstractmethod


class ActionContext:
    """动作执行的上下文——持有设备适配器和其他资源"""
    def __init__(self, device: BaseDeviceAdapter):
        self.device = device
        self.variables = {}  # 跨步骤共享数据


class ActionHandler(ABC):
    @abstractmethod
    def execute(self, args: dict, ctx: ActionContext): ...


class ClickHandler(ActionHandler):
    def execute(self, args, ctx):
        x = args.get("x", 0)
        y = args.get("y", 0)
        ctx.device.click(x, y)


class TypeHandler(ActionHandler):
    def execute(self, args, ctx):
        ctx.device.type(args.get("text", ""))


class OpenAppHandler(ActionHandler):
    def execute(self, args, ctx):
        ctx.device.open_app(args.get("app_id", ""))


class WaitHandler(ActionHandler):
    def execute(self, args, ctx):
        time.sleep(args.get("time", 2))


class TerminateHandler(ActionHandler):
    def execute(self, args, ctx):
        pass  # 由 ReAct 引擎处理


class SwipeHandler(ActionHandler):
    def execute(self, args, ctx):
        ctx.device.swipe(args.get("x1", 0), args.get("y1", 0),
                         args.get("x2", 0), args.get("y2", 0))


class ActionDispatcher:
    """策略模式分发器——替代 if/elif 链"""

    def __init__(self):
        self._handlers: dict[str, ActionHandler] = {
            "click": ClickHandler(),
            "type": TypeHandler(),
            "open_app": OpenAppHandler(),
            "wait": WaitHandler(),
            "terminate": TerminateHandler(),
            "swipe": SwipeHandler(),
            "press_back": PressBackHandler(),
            "press_home": PressHomeHandler(),
            "assert": AssertHandler(),
        }

    def register(self, name: str, handler: ActionHandler):
        """注册新动作（扩展点）"""
        self._handlers[name] = handler

    def execute(self, name: str, args: dict, ctx: ActionContext):
        if name not in self._handlers:
            return False  # 让调用方处理未知动作
        self._handlers[name].execute(args, ctx)
        return True
```

### 6.2 MCP 集成层

```
class MCPTool:
    """单个 MCP 工具的封装"""

    def __init__(self, name: str, description: str,
                 input_schema: dict, handler: ActionHandler):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def to_openai_tool(self) -> dict:
        """转成 OpenAI 工具格式，用于注入 System Prompt"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }

    def to_system_prompt_block(self) -> str:
        """生成 <tools> 块"""
        return json.dumps(self.to_openai_tool(), indent=2)


class MCPServer:
    """MCP Server 封装——管理一组 MCPTool"""

    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, MCPTool] = {}

    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool

    def get_tool_schemas(self) -> list[dict]:
        return [t.to_openai_tool() for t in self.tools.values()]

    def get_system_prompt(self) -> str:
        lines = ["<tools>"]
        for t in self.tools.values():
            lines.append(t.to_system_prompt_block())
        lines.append("</tools>")
        return "\n".join(lines)


def create_mobile_device_server(device: BaseDeviceAdapter) -> MCPServer:
    """创建设备控制 MCP Server"""
    server = MCPServer("mobile_device")
    dispatcher = ActionDispatcher()

    server.register_tool(MCPTool(
        "click", "Click an element on screen",
        {"type": "object", "properties": {
            "x": {"type": "integer"}, "y": {"type": "integer"}
        }, "required": ["x", "y"]},
        ClickHandler(),
    ))
    server.register_tool(MCPTool(
        "type", "Input text",
        {"type": "object", "properties": {
            "text": {"type": "string"}
        }, "required": ["text"]},
        TypeHandler(),
    ))
    server.register_tool(MCPTool(
        "open_app", "Open an installed app",
        {"type": "object", "properties": {
            "app_id": {"type": "string"}
        }, "required": ["app_id"]},
        OpenAppHandler(),
    ))
    server.register_tool(MCPTool(
        "wait", "Wait for specified seconds",
        {"type": "object", "properties": {
            "time": {"type": "number", "default": 2}
        }, "required": []},
        WaitHandler(),
    ))
    server.register_tool(MCPTool(
        "swipe", "Swipe on screen",
        {"type": "object", "properties": {
            "x1": {"type": "integer"}, "y1": {"type": "integer"},
            "x2": {"type": "integer"}, "y2": {"type": "integer"}
        }, "required": ["x1", "y1", "x2", "y2"]},
        SwipeHandler(),
    ))
    return server
```

---

## 7. 平台构建：轨迹录制 + 脚本生成

### 7.1 轨迹录制器

```
from dataclasses import dataclass, field
from typing import Optional
import json
import time


@dataclass
class TraceStep:
    step_id: int
    tool_name: str
    arguments: dict
    result: str  # "success" | "failure"
    error: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: float = 0.0


class TraceStore:
    """轨迹录制器——记录每一步的执行信息"""

    def __init__(self, task_id: str, platform: str = "android"):
        self.task_id = task_id
        self.platform = platform
        self.steps: list[TraceStep] = []
        self.final_status: Optional[str] = None
        self._fail_count = 0

    def record(self, tool_name: str, arguments: dict,
               screenshot_path: str = None) -> TraceStep:
        step = TraceStep(
            step_id=len(self.steps) + 1,
            tool_name=tool_name,
            arguments=dict(arguments),
            result="success",
            screenshot_path=screenshot_path,
            timestamp=time.time(),
        )
        self.steps.append(step)
        return step

    def record_failure(self, tool_name: str, arguments: dict,
                       error: str, screenshot_path: str = None) -> TraceStep:
        step = TraceStep(
            step_id=len(self.steps) + 1,
            tool_name=tool_name,
            arguments=dict(arguments),
            result="failure",
            error=error,
            screenshot_path=screenshot_path,
            timestamp=time.time(),
        )
        self.steps.append(step)
        self._fail_count += 1
        return step

    def finalize(self, status: str):
        self.final_status = status

    def clean(self) -> list[TraceStep]:
        """轨迹清理：去掉失败步骤，用最后成功的参数"""
        successful = [s for s in self.steps if s.result == "success"]
        return successful

    def to_json(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": self.task_id,
                "platform": self.platform,
                "steps": [
                    {"step_id": s.step_id, "tool": s.tool_name,
                     "arguments": s.arguments, "result": s.result}
                    for s in self.steps
                ],
                "final_status": self.final_status,
            }, f, ensure_ascii=False, indent=2)

    def to_readable_text(self) -> str:
        lines = [f"Task: {self.task_id}", f"Platform: {self.platform}", ""]
        for s in self.clean():
            args_str = ", ".join(f"{k}={v}" for k, v in s.arguments.items())
            lines.append(f"  Step {s.step_id}: {s.tool_name}({args_str})")
        return "\n".join(lines)
```

### 7.2 脚本生成器

```
from abc import ABC, abstractmethod


class FrameworkEmitter(ABC):
    """脚本生成器基类——模板方法模式"""

    @abstractmethod
    def _step_to_code(self, step: TraceStep) -> str: ...

    @abstractmethod
    def _imports(self) -> str: ...

    @abstractmethod
    def _file_extension(self) -> str: ...

    def emit(self, trace: TraceStore) -> str:
        steps = trace.clean()
        lines = [self._imports(), ""]

        func_lines = ["def test_main():"]
        for step in steps:
            code = self._step_to_code(step)
            for line in code.split("\n"):
                func_lines.append(f"    {line}")
            func_lines.append("    time.sleep(1)")

        func_lines.append("")
        func_lines.append('if __name__ == "__main__":')
        func_lines.append("    test_main()")

        lines.extend(func_lines)
        return "\n".join(lines)


class UIAutomator2Emitter(FrameworkEmitter):
    """输出 uiautomator2 脚本"""

    def _imports(self) -> str:
        return "import uiautomator2 as u2\nimport time\n\nd = u2.connect()"

    def _file_extension(self) -> str:
        return ".py"

    def _step_to_code(self, step: TraceStep) -> str:
        if step.tool_name == "click":
            return 'd.click({x}, {y})'.format(**step.arguments)
        elif step.tool_name == "type":
            return 'd(text="{text}").set_text("{text}")'.format(**step.arguments)
        elif step.tool_name == "open_app":
            return 'd.app_start("{app_id}")'.format(**step.arguments)
        elif step.tool_name == "press_back":
            return "d.press('back')"
        elif step.tool_name == "wait":
            return "time.sleep({time})".format(**step.arguments)
        elif step.tool_name == "swipe":
            return 'd.swipe({x1}, {y1}, {x2}, {y2})'.format(**step.arguments)
        elif step.tool_name == "assert":
            return 'assert d(text="{expected}").exists'.format(**step.arguments)
        return f"# TODO: {step.tool_name}"


class XCUITestEmitter(FrameworkEmitter):
    """输出 XCUITest Swift 脚本"""

    def _imports(self) -> str:
        return "import XCTest\n\nlet app = XCUIApplication()"

    def _file_extension(self) -> str:
        return ".swift"

    def _step_to_code(self, step: TraceStep) -> str:
        if step.tool_name == "click":
            return f'app.coordinate(withNormalizedOffset: CGVector(dx: {step.arguments.get("x", 0)}/1000, dy: {step.arguments.get("y", 0)}/1000)).tap()'
        elif step.tool_name == "type":
            return f'app.textFields.element.tap()\napp.textFields.element.typeText("{step.arguments.get("text", "")}")'
        elif step.tool_name == "press_back":
            return "// iOS: no universal back button"
        elif step.tool_name == "wait":
            return f'sleep({step.arguments.get("time", 2)})'
        return f"// TODO: {step.tool_name}"


class HarmonyOSEmitter(FrameworkEmitter):
    """输出鸿蒙 UI Test Java 脚本"""

    def _imports(self) -> str:
        return "import ohos.aafwk.ability.delegation.AbilityDelegator;\nimport org.junit.Test;"

    def _file_extension(self) -> str:
        return ".java"

    def _step_to_code(self, step: TraceStep) -> str:
        x = step.arguments.get("x", 0)
        y = step.arguments.get("y", 0)
        if step.tool_name == "click":
            return f'delegator.executeShellCommand("uitest click -x {x} -y {y}");'
        elif step.tool_name == "type":
            return f'delegator.executeShellCommand("uitest input -t {step.arguments.get("text", "")}");'
        elif step.tool_name == "wait":
            return f'Thread.sleep({step.arguments.get("time", 2) * 1000});'
        return f'// TODO: {step.tool_name}'


def create_emitter(framework: str) -> FrameworkEmitter:
    if framework == "uiautomator2":
        return UIAutomator2Emitter()
    elif framework == "xctest":
        return XCUITestEmitter()
    elif framework == "harmonyos_uitest":
        return HarmonyOSEmitter()
    raise ValueError(f"Unsupported framework: {framework}")
```

---

## 8. 平台构建：最小可运行示例

将以上所有组件串起来，形成一个完整的最小平台：

```
"""
最小可运行的 Agent 平台——基于 Mobile-Agent-v3.5 提取的代码
可直接在 Android 设备上执行
"""
import sys
import json
import time
from pathlib import Path

# 假设以上所有类定义在同一文件或导入
# 实际使用时可拆分为多模块

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb_path", required=True)
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--base_url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--output", default="./output")
    parser.add_argument("--max_steps", type=int, default=50)
    args = parser.parse_args()

    # 1. 初始化
    device = AndroidAdapter(args.adb_path)
    vlm = VLMClient(args.api_key, args.base_url, args.model)
    server = create_mobile_device_server(device)
    msg_builder = MessageBuilder(server.get_tool_schemas())

    # 2. 准备输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. 初始化轨迹录制器
    trace = TraceStore(task_id="agent_run_001", platform="android")

    # 4. 执行 ReAct 循环
    engine = ReActEngine(device, vlm, msg_builder, max_steps=args.max_steps)
    history = []
    final_status = "failure"

    for step in range(args.max_steps):
        print(f"\n{'='*60}")
        print(f"  STEP {step}")
        print(f"{'='*60}")

        # Screenshot
        screenshot = str(output_dir / f"step_{step}.png")
        if not device.screenshot(screenshot):
            continue

        # VLM
        messages = msg_builder.build(args.instruction, screenshot, history)
        response = vlm.chat(messages)
        print(f"[VLM] {response[:300]}")

        # Parse
        try:
            action = ActionParser.parse(response)
            name = action.get("name", "")
            args_dict = action.get("arguments", {})
        except ValueError as e:
            print(f"[PARSE ERROR] {e}")
            trace.record_failure("parse", {"raw": response[:200]}, str(e))
            continue

        # Execute & record
        try:
            if name == "terminate":
                trace.record("terminate", args_dict, screenshot)
                final_status = "success"
                break
            engine._execute(name, args_dict)
            trace.record(name, args_dict, screenshot)
        except Exception as e:
            print(f"[EXEC ERROR] {e}")
            trace.record_failure(name, args_dict, str(e), screenshot)
            continue

        history.append({"step": step, "image": screenshot, "output": response})
        time.sleep(2)

    # 5. 生成脚本
    trace.finalize(final_status)
    trace.to_json(str(output_dir / "trace.json"))

    emitter = UIAutomator2Emitter()
    script = emitter.emit(trace)
    script_path = output_dir / "generated_script.py"
    script_path.write_text(script, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  FINAL STATUS: {final_status}")
    print(f"  Trace: {output_dir / 'trace.json'}")
    print(f"  Script: {script_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
```

运行方式：

```bash
python agent_platform.py \
    --adb_path "/path/to/adb" \
    --api_key "sk-xxx" \
    --base_url "https://dashscope.aliyuncs.com/compatible-mode/v1" \
    --model "qwen-vl-plus" \
    --instruction "打开淘宝搜索手机，截图搜索结果页" \
    --output "./output"
```

输出：

```
output/
├── step_0.png          # 每一步的截图
├── step_1.png
├── ...
├── trace.json          # 执行轨迹（JSON）
└── generated_script.py # 生成的 uiautomator2 脚本
```
