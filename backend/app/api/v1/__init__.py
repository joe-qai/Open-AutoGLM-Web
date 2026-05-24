"""API v1 module."""

from .tasks import router as tasks_router
from .devices import router as devices_router
from .reports import router as reports_router
from .websocket import router as websocket_router
from .scripts import router as scripts_router
from .apks import router as apks_router
from .logs import router as logs_router
