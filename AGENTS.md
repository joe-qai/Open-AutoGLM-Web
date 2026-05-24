# AGENTS.md — Open-AutoGLM Web Platform

This repo is a fork of Open-AutoGLM with a frontend+backend web platform on top of the `phone_agent` core library.

## Subsystems & Toolchains

| Subsystem | Location | Tech | Install | Run |
|-----------|----------|------|---------|-----|
| Core lib | `phone_agent/` | Python, OpenAI+Anthropic SDK | `pip install -e .` | `python main.py` |
| Backend | `backend/` | FastAPI, SQLAlchemy, aiosqlite | `pip install -r backend/requirements.txt` | `python run.py` (port 8000) |
| Frontend | `frontend/` | React 18, Vite, Tailwind, TS, zustand, react-query, recharts | `cd frontend && npm install` | `npm run dev` (port 3000) |
| Launcher | `start_all.bat` | Windows batch | — | Start backend + frontend together |

## Dev Commands

```bash
# Full setup
pip install -r requirements.txt
pip install -e .
pip install -r backend/requirements.txt
cd frontend && npm install

# Run backend (FastAPI)
cd backend && python run.py

# Run frontend (Vite, proxies /api to :8000)
cd frontend && npm run dev

# Standalone phone_agent CLI (no web platform needed)
python main.py --base-url <URL> --model <NAME> "task"
python main.py --device-type hdc ...
python ios.py --wda-url http://localhost:8100 ...

# Tests
pytest                      # phone_agent core
cd backend && pytest        # backend (asyncio_mode=auto)

# Lint (from root)
ruff check --fix . && ruff format .
pre-commit run --all-files  # ruff, typos, pymarkdown (excludes config/apps.py)
```

## Web Platform Architecture

**Backend layers** (`backend/app/core/layers/`): Perception → Decision → Action → Memory → Verification
**Backend agents** (`backend/app/core/agent/`): Manager, Executor, Reflector, Finder — coordinated by `AgentEngine`
**Backend API** (`backend/app/api/v1/`): tasks, devices, reports, scripts, apks, projects, settings, model_configs, logs. WebSocket at `/ws`. Audit log middleware on all requests.
**Backend config**: `backend/app/config.py` uses `pydantic-settings` with `env_prefix="PHONE_AGENT_"` (reads `.env`).

**Frontend structure** (`frontend/src/`): `pages/` (route pages), `components/` (reusable), `services/api.ts` (axios), `services/ws.ts` (websocket), `stores/` (zustand).

**Database**: `backend/app.db` (aiosqlite, auto-created on first run).

## phone_agent Core (for agents)

Core loop in `PhoneAgent._execute_step()`: screenshot → detect app → build multimodal message → call VLM → `parse_action()` → `ActionHandler.execute()` → repeat. Format auto-detected: `{` prefix = JSON, `do`/`finish` prefix = pseudo-code.

JSON markers in `model/client.py`: XML tags `<json_answer>`/`<json_think>` (constants `JSON_ANSWER_OPEN`, `JSON_THINK_OPEN`). Imported by prompt files.

Device abstraction: `DeviceFactory` → `adb/` (Android) / `hdc/` (HarmonyOS) / `xctest/` (iOS). Set via `set_device_type(DeviceType.ADB|HDC|IOS)`.

## Gotchas

- JSON markers in `CLAUDE.md` line 78 used to claim Bengali numerals — they are now XML tags. Source of truth: `phone_agent/model/client.py`.
- `config/apps.py` is a very large app mapping file, excluded from pre-commit.
- Backend and `phone_agent` have separate `requirements.txt` files — both must be installed.
- Frontend dev server requires the backend to be running (proxies `/api` to port 8000).
- Python 3.10+ only, uses `str | None` syntax (not `Optional`).
