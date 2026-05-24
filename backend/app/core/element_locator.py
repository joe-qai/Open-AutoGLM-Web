from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class LocatorType(str, Enum):
    RESOURCE_ID = "resource_id"
    CONTENT_DESC = "content_desc"
    TEXT = "text"
    TEXT_CONTAINS = "text_contains"
    CLASS_NAME = "class_name"
    SEMANTIC = "semantic"
    COORDINATES = "coordinates"


@dataclass
class ElementLocator:
    locator_type: LocatorType
    value: str
    index: int = 0


@dataclass
class LocateResult:
    success: bool
    x: int = 0
    y: int = 0
    element_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class MultiStrategyElementLocator:
    def __init__(self, device_adapter):
        self.device = device_adapter

    def locate(self, locator: ElementLocator) -> LocateResult:
        dispatch = {
            LocatorType.RESOURCE_ID: self._locate_by_resource_id,
            LocatorType.CONTENT_DESC: self._locate_by_content_desc,
            LocatorType.TEXT: self._locate_by_text,
            LocatorType.TEXT_CONTAINS: self._locate_by_text_contains,
            LocatorType.CLASS_NAME: self._locate_by_class_name,
            LocatorType.SEMANTIC: self._locate_by_semantic,
            LocatorType.COORDINATES: self._locate_by_coordinates,
        }
        handler = dispatch.get(locator.locator_type)
        if not handler:
            return LocateResult(
                success=False,
                error_message=f"Unknown locator type: {locator.locator_type}",
            )
        return handler(locator.value, locator.index)

    def _locate_by_resource_id(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(resourceId=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True,
                    x=cx,
                    y=cy,
                    element_info={"resource_id": value, "bounds": bounds},
                )
        except Exception:
            pass
        return LocateResult(
            success=False, error_message=f"resource_id not found: {value}"
        )

    def _locate_by_content_desc(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(description=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True,
                    x=cx,
                    y=cy,
                    element_info={"content_desc": value, "bounds": bounds},
                )
        except Exception:
            pass
        return LocateResult(
            success=False, error_message=f"content_desc not found: {value}"
        )

    def _locate_by_text(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(text=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True,
                    x=cx,
                    y=cy,
                    element_info={"text": value, "bounds": bounds},
                )
        except Exception:
            pass
        return LocateResult(success=False, error_message=f"text not found: {value}")

    def _locate_by_text_contains(self, value: str, index: int = 0) -> LocateResult:
        try:
            element = self.device(textContains=value)
            if element.exists:
                bounds = element.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True,
                    x=cx,
                    y=cy,
                    element_info={"text_contains": value, "bounds": bounds},
                )
        except Exception:
            pass
        return LocateResult(
            success=False, error_message=f"text_contains not found: {value}"
        )

    def _locate_by_class_name(self, value: str, index: int = 0) -> LocateResult:
        try:
            elements = self.device(className=value)
            if elements.count > index:
                el = elements[index]
                bounds = el.bounds()
                cx = (bounds[0] + bounds[2]) // 2
                cy = (bounds[1] + bounds[3]) // 2
                return LocateResult(
                    success=True,
                    x=cx,
                    y=cy,
                    element_info={
                        "class_name": value,
                        "index": index,
                        "bounds": bounds,
                    },
                )
        except Exception:
            pass
        return LocateResult(
            success=False, error_message=f"class_name[{index}] not found: {value}"
        )

    def _locate_by_semantic(self, value: str, index: int = 0) -> LocateResult:
        return LocateResult(
            success=False, error_message="semantic locator not yet implemented"
        )

    def _locate_by_coordinates(self, value: str, index: int = 0) -> LocateResult:
        try:
            parts = value.split(",")
            if len(parts) == 2:
                x, y = int(parts[0]), int(parts[1])
                return LocateResult(
                    success=True, x=x, y=y, element_info={"coordinates": [x, y]}
                )
        except (ValueError, IndexError):
            pass
        return LocateResult(
            success=False, error_message=f"invalid coordinates: {value}"
        )

    def find_element(self, criteria: dict) -> Optional[dict]:
        locator_type_map = {
            "text": LocatorType.TEXT,
            "resource_id": LocatorType.RESOURCE_ID,
            "content_desc": LocatorType.CONTENT_DESC,
            "class_name": LocatorType.CLASS_NAME,
        }
        for key, lt in locator_type_map.items():
            if key in criteria:
                result = self.locate(ElementLocator(lt, criteria[key]))
                if result.success:
                    return result.element_info
        return None
