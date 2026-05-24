# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoPhone (Phone Agent) is an AI-powered phone automation framework by Zhipu AI. It uses a vision-language model (AutoPhone-Phone-9B) to understand phone screens and automate tasks on Android, HarmonyOS, and iOS devices via ADB/HDC/XCTest. Users describe tasks in natural language (e.g., "打开小红书搜索美�?), and the agent captures screenshots, sends them to the VLM, parses actions, and executes device operations in a loop.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install with dev dependencies (pytest, black, mypy, ruff)
pip install -e ".[dev]"

# Run the agent (Android/HarmonyOS) �?AutoPhone native model
python main.py --base-url <MODEL_API_URL> --model <MODEL_NAME>
python main.py --base-url <MODEL_API_URL> "打开微信查看消息"

# Run the agent with a generic cloud model (JSON format)
python main.py --base-url <MODEL_API_URL> --model <MODEL_NAME> --format json "打开微信查看消息"

# Run the agent (iOS)
python ios.py --base-url <MODEL_API_URL> --wda-url http://localhost:8100

# iOS with JSON format
python ios.py --base-url <MODEL_API_URL> --format json --wda-url http://localhost:8100

# List supported apps
python main.py --list-apps

# Run pre-commit hooks
pre-commit run --all-files

# Lint with ruff
ruff check --fix .
ruff format .

# Check spelling
typos

# Check markdown
pymarkdown fix .

# Run tests (if pytest installed)
pytest
```

## Architecture

### Core Agent Loop

Both `PhoneAgent` (Android) and `IOSPhoneAgent` follow the same loop in `_execute_step`:
1. Capture screenshot + detect current app
2. Build OpenAI-format messages (system prompt + user message with screenshot)
3. Call VLM via `ModelClient.request()` (streaming, parses thinking vs action)
4. Parse action string into dict via `parse_action()`
5. Execute action via `ActionHandler` or `IOSActionHandler`
6. Strip images from context to save space, append assistant message
7. Repeat until `finish(message=...)` or max_steps

### Device Abstraction (Factory Pattern)

`DeviceFactory` in `device_factory.py` is the key abstraction layer. It delegates to one of three device modules:
- **`phone_agent/adb/`** �?Android via ADB (connection.py, device.py, input.py, screenshot.py)
- **`phone_agent/hdc/`** �?HarmonyOS via HDC (same module structure)
- **`phone_agent/xctest/`** �?iOS via WebDriverAgent/XCUITest (same module structure)

Each module exposes identical top-level functions: `get_screenshot`, `tap`, `swipe`, `type_text`, `back`, `home`, `launch_app`, etc. The factory is set globally via `set_device_type(DeviceType.ADB|HDC|IOS)`.

### Model Interaction

`ModelClient` in `model/client.py` uses OpenAI-compatible streaming API. It parses model output into `(thinking, action)` and supports two output formats:
- **`pseudo`** (default, AutoPhone native): Python pseudo-code with markers `do(action=`, `finish(message=`, and `<answer>` tags
- **`json`** (generic cloud models): JSON action objects with XML tag markers `<json_think>`/`<json_answer>` defined as module constants (`JSON_THINK_OPEN`, `JSON_ANSWER_OPEN` etc. in `model/client.py`). Also has a regex fallback to extract raw JSON from untagged model output.

Format is selected via `AgentConfig.format` or `--format` CLI arg. `parse_action()` in `actions/handler.py` auto-detects: `{` prefix �?JSON, `do`/`finish` prefix �?pseudo-code. `MessageBuilder` constructs multimodal messages with base64 screenshots.

### Action Handling

`ActionHandler` (Android/HarmonyOS) and `IOSActionHandler` (iOS) in `actions/` map action names to handler methods. Supported actions: Launch, Tap, Type, Type_Name, Swipe, Back, Home, Double Tap, Long Press, Wait, Take_over, Note, Call_API, Interact. Coordinates use a 0-999 relative system converted to absolute pixels via `_convert_relative_to_absolute`.

### Config System

`phone_agent/config/` contains:
- **`prompts_zh.py`/`prompts_en.py`** �?System prompts for both pseudo-code (`SYSTEM_PROMPT`) and JSON (`SYSTEM_PROMPT_JSON`) formats. JSON prompts import markers from `model/client.py` to stay in sync with the parser. `get_system_prompt(lang, format)` selects the right prompt.
- **`apps.py`/`apps_harmonyos.py`/`apps_ios.py`** �?App name �?package/bundle ID mappings
- **`i18n.py`** �?Chinese/English UI message strings
- **`timing.py`** �?Configurable timing delays (all overridable via `PHONE_AGENT_*` env vars)

### CLI Entry Points

- **`main.py`** �?Android/HarmonyOS CLI with argparse, system requirement checks, interactive mode
- **`ios.py`** �?iOS CLI, similar structure but checks libimobiledevice + WebDriverAgent

### Web Platform (LOCKIN)

This repo adds a web platform on top of the core `phone_agent` library:

- **`backend/`** — FastAPI server (port 8000) with SQLAlchemy + aiosqlite. Layered architecture: Perception/Decision/Action/Memory/Verification layers + multi-agent system (Manager/Executor/Reflector/Finder agents). API routes under `/api/v1/` (tasks, devices, reports, scripts, apks, projects, settings, model_configs, logs). Websocket at `/ws`. Entry: `python run.py`.
- **`frontend/`** — React 18 + Vite + TypeScript + Tailwind CSS SPA (port 3000). Uses zustand (state), @tanstack/react-query (API), recharts (charts), framer-motion (animations). Proxies `/api` to `:8000` in dev. Entry: `npm run dev`.
- **`start_all.bat`** — Windows launcher for both services.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `PHONE_AGENT_BASE_URL` | `http://localhost:8000/v1` | Model API URL |
| `PHONE_AGENT_MODEL` | `AutoPhone-phone-9b` | Model name |
| `PHONE_AGENT_API_KEY` | `EMPTY` | API key |
| `PHONE_AGENT_MAX_STEPS` | `100` | Max steps per task |
| `PHONE_AGENT_DEVICE_ID` | (auto) | Device ID for multi-device |
| `PHONE_AGENT_DEVICE_TYPE` | `adb` | Device type (`adb`/`hdc`/`ios`) |
| `PHONE_AGENT_LANG` | `cn` | Language (`cn`/`en`) |
| `PHONE_AGENT_FORMAT` | `pseudo` | Output format (`pseudo`/`json`) |
| `PHONE_AGENT_WDA_URL` | `http://localhost:8100` | iOS WebDriverAgent URL |
| `PHONE_AGENT_*_DELAY` | various | All timing delays in `timing.py` |

## Key Conventions

- Python 3.10+ required; uses `str | None` union syntax (not `Optional`)
- Pre-commit runs ruff (lint + format), typos (spelling), pymarkdown (markdown lint)
- The `config/apps.py` file is excluded from pre-commit (large app mapping data)
- Model output supports two action formats: pseudo-code (`do(action="Tap", element=[x,y])`) or JSON (`{"action": "Tap", "element": [x,y]}`), selectable via `--format` flag
- JSON format markers are defined as constants in `model/client.py` (XML tags: `<json_think>`, `<json_answer>`, etc., imported by prompt files as `JSON_THINK_OPEN`/`JSON_ANSWER_OPEN`) and imported by prompt files to stay in sync
- Relative coordinate system: 0-999 mapped to screen pixels (top-left origin)
- Bilingual: all user-facing strings support `cn` (Chinese) and `en` (English)
