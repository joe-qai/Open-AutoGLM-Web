"""API v1 module."""

from .tasks import router as tasks_router
from .devices import router as devices_router
from .reports import router as reports_router
from .websocket import router as websocket_router
from .scripts import router as scripts_router
from .apks import router as apks_router
from .projects import router as projects_router
from .settings import router as settings_router
from .model_configs import router as model_configs_router
from .logs import router as logs_router
from .control import router as control_router

__all__ = [
    "tasks_router",
    "devices_router",
    "reports_router",
    "websocket_router",
    "scripts_router",
    "apks_router",
    "projects_router",
    "settings_router",
    "model_configs_router",
    "logs_router",
    "control_router",
]
