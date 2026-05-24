from dataclasses import dataclass
from typing import Tuple, Optional, List
import xml.etree.ElementTree as ET
import re


@dataclass
class UIElement:
    resource_id: str = ""
    class_name: str = ""
    text: str = ""
    content_desc: str = ""
    bounds: Tuple[int, int, int, int] = (0, 0, 0, 0)
    enabled: bool = True
    clickable: bool = False
    focused: bool = False

    @property
    def center(self) -> Tuple[int, int]:
        return (
            (self.bounds[0] + self.bounds[2]) // 2,
            (self.bounds[1] + self.bounds[3]) // 2,
        )

    @property
    def has_resource_id(self) -> bool:
        return bool(self.resource_id)

    @property
    def priority_key(self) -> int:
        if self.resource_id:
            return 0
        if self.content_desc:
            return 1
        if self.text:
            return 2
        return 3


class UITreeExtractor:
    """Extracts Android UI hierarchy XML and converts to structured text for LLM prompts."""

    def __init__(self, device_adapter):
        self.device = device_adapter

    def extract(self) -> str:
        """Get raw UI tree XML from device."""
        return self.device.dump_ui_tree()

    def to_text(self, ui_xml: str, max_elements: int = 30) -> str:
        """Convert UI tree XML to structured text description."""
        elements = self._parse_xml(ui_xml)
        sorted_elements = self._sort_by_priority(elements)

        lines = []
        lines.append("=== 屏幕概览 ===")
        try:
            display = self.device.get_display_info()
            lines.append(f"分辨率: {display.width}x{display.height}")
        except Exception:
            lines.append("分辨率: unknown")
        try:
            lines.append(f"当前应用: {self.device.get_current_app()}")
        except Exception:
            lines.append("当前应用: unknown")
        lines.append("")
        lines.append("=== 可交互元素 ===")

        clickable = [e for e in sorted_elements if e.clickable and e.enabled]
        for i, elem in enumerate(clickable[:max_elements]):
            prefix = "+" if elem.has_resource_id else "-"
            attrs = []
            if elem.resource_id:
                attrs.append(f"id={elem.resource_id}")
            if elem.text:
                attrs.append(f"text={elem.text}")
            if elem.content_desc:
                attrs.append(f"desc={elem.content_desc}")
            if elem.class_name:
                attrs.append(f"type={elem.class_name.split('.')[-1]}")
            x, y = elem.center
            lines.append(f"{prefix}[{i}] {' | '.join(attrs)} @({x},{y})")

        if len(clickable) > max_elements:
            lines.append(f"... (还有 {len(clickable) - max_elements} 个元素)")

        inputs = [e for e in elements if "EditText" in e.class_name and e.enabled]
        if inputs:
            lines.append("")
            lines.append("=== 输入框 ===")
            for i, elem in enumerate(inputs):
                label = elem.resource_id or elem.class_name.split(".")[-1]
                lines.append(f"  [{i}] {label} @({elem.center[0]},{elem.center[1]})")

        return "\n".join(lines)

    def _parse_xml(self, ui_xml: str) -> List[UIElement]:
        """Parse UI tree XML string into list of UIElement."""
        elements = []
        if not ui_xml or not ui_xml.strip():
            return elements
        try:
            root = ET.fromstring(ui_xml)
            self._parse_element(root, elements)
        except ET.ParseError:
            pass
        except Exception:
            pass
        return elements

    def _parse_element(self, element: ET.Element, results: List[UIElement]):
        """Recursively parse XML element tree."""
        attrib = element.attrib
        bounds_str = attrib.get("bounds", "[0,0][0,0]")
        ui_elem = UIElement(
            resource_id=attrib.get("resource-id", ""),
            class_name=attrib.get("class", ""),
            text=attrib.get("text", ""),
            content_desc=attrib.get("content-desc", ""),
            bounds=self._parse_bounds(bounds_str),
            enabled=attrib.get("enabled", "true") == "true",
            focused=attrib.get("focused", "false") == "true",
            clickable=attrib.get("clickable", "false") == "true",
        )
        results.append(ui_elem)
        for child in element:
            self._parse_element(child, results)

    def _parse_bounds(self, bounds_str: str) -> Tuple[int, int, int, int]:
        """Parse bounds string like [0,0][1080,2400] into tuple."""
        match = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if match:
            return (
                int(match.group(1)), int(match.group(2)),
                int(match.group(3)), int(match.group(4)),
            )
        return (0, 0, 0, 0)

    def _sort_by_priority(self, elements: List[UIElement]) -> List[UIElement]:
        """Sort elements by locator priority (resource_id > desc > text > class_name)."""
        return sorted(elements, key=lambda e: e.priority_key)
