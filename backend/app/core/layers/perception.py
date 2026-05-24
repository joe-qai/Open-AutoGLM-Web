"""Perception layer for the Agent architecture."""

import os
import base64
import time
import tempfile
from typing import List, Dict, Any
from dataclasses import dataclass

from ..adapters.base import BaseDeviceAdapter, UIElement


@dataclass
class PerceptionResult:
    """Result of perception operation."""

    screenshot_base64: str
    screenshot_path: str
    ui_elements: List[UIElement]
    current_app: str
    ui_text: str = ""
    timestamp: float = 0.0


class PerceptionLayer:
    """Perception layer - captures device state and UI elements."""

    def __init__(self, adapter: BaseDeviceAdapter):
        self.adapter = adapter
        self.screenshot_dir = "./screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        from app.core.ui_tree import UITreeExtractor

        self.ui_extractor = UITreeExtractor(adapter)

    def perceive(self, step_index: int = 0) -> PerceptionResult:
        """Capture current device state."""
        timestamp = time.time()
        screenshot_path = os.path.join(
            self.screenshot_dir, f"step_{step_index:03d}_{int(timestamp)}.png"
        )

        self.adapter.get_screenshot(screenshot_path)

        with open(screenshot_path, "rb") as f:
            screenshot_base64 = base64.b64encode(f.read()).decode()

        ui_elements = self.adapter.get_element_tree(screenshot_path)
        current_app = self.adapter.get_current_app()
        ui_text = ""
        try:
            ui_xml = self.ui_extractor.extract()
            ui_text = self.ui_extractor.to_text(ui_xml)
        except Exception:
            ui_text = ""

        return PerceptionResult(
            screenshot_base64=screenshot_base64,
            screenshot_path=screenshot_path,
            ui_elements=ui_elements,
            current_app=current_app,
            ui_text=ui_text,
            timestamp=timestamp,
        )

    def perceive_lightweight(self) -> Dict[str, Any]:
        """Lightweight perception without saving screenshot to disk."""
        screenshot_base64 = self.adapter.get_screenshot_base64()
        current_app = self.adapter.get_current_app()

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name

        self.adapter.get_screenshot(temp_path)
        ui_elements = self.adapter.get_element_tree(temp_path)
        os.unlink(temp_path)

        ui_text = ""
        try:
            ui_xml = self.ui_extractor.extract()
            ui_text = self.ui_extractor.to_text(ui_xml)
        except Exception:
            ui_text = ""

        return {
            "screenshot_base64": screenshot_base64,
            "ui_elements": [
                {
                    "index": e.index,
                    "text": e.text,
                    "resource_id": e.resource_id,
                    "content_desc": e.content_desc,
                    "bbox_normalized": e.bbox_normalized,
                    "clickable": e.clickable,
                }
                for e in ui_elements
            ],
            "current_app": current_app,
            "ui_text": ui_text,
        }

    def get_ui_elements_summary(self) -> str:
        """Get a summary of current UI elements."""
        result = self.perceive_lightweight()
        elements = result.get("ui_elements", [])
        summary = "\n".join(
            [
                f"- [{e.get('index')}] text='{e.get('text', '')[:30]}', id='{e.get('resource_id', '')[:30]}'"
                for e in elements[:20]
            ]
        )
        return summary
