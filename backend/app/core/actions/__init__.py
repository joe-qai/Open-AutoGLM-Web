# -*- coding: utf-8 -*-
"""Action handling module for backend automation pipeline.

Exports the core action handler classes, result dataclass, and parsing utilities
used to translate VLM model output into device operations.
"""

from backend.app.core.actions.handler import (
    ActionHandler,
    ActionResult,
    parse_action,
    do,
    finish,
)
from backend.app.core.actions.handler_ios import IOSActionHandler

__all__ = [
    "ActionHandler",
    "ActionResult",
    "IOSActionHandler",
    "parse_action",
    "do",
    "finish",
]
