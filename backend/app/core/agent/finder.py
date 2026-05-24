"""Finder Agent - locates elements and apps on device."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..layers.perception import PerceptionLayer


@dataclass
class FoundElement:
    """Information about a found element."""
    index: int
    text: str
    resource_id: str
    content_desc: str
    bbox: Dict[str, float]
    clickable: bool
    confidence: float


@dataclass
class FoundApp:
    """Information about a found application."""
    package_name: str
    name: str
    installed: bool
    version: Optional[str] = None


class FinderAgent:
    """Finder Agent - locates UI elements and applications."""
    
    def __init__(self, adapter):
        self.perception = PerceptionLayer(adapter)
        self.adapter = adapter
    
    def find_element(self, criteria: Dict) -> Optional[FoundElement]:
        """Find a UI element matching criteria."""
        perception = self.perception.perceive_lightweight()
        elements = perception.get("ui_elements", [])
        
        for element in elements:
            if self._matches_criteria(element, criteria):
                confidence = self._calculate_confidence(element, criteria)
                return FoundElement(
                    index=element.get("index", 0),
                    text=element.get("text", ""),
                    resource_id=element.get("resource_id", ""),
                    content_desc=element.get("content_desc", ""),
                    bbox=element.get("bbox_normalized", {}),
                    clickable=element.get("clickable", False),
                    confidence=confidence
                )
        
        return None
    
    def find_elements(self, criteria: Dict) -> List[FoundElement]:
        """Find all UI elements matching criteria."""
        perception = self.perception.perceive_lightweight()
        elements = perception.get("ui_elements", [])
        
        found = []
        for element in elements:
            if self._matches_criteria(element, criteria):
                confidence = self._calculate_confidence(element, criteria)
                found.append(FoundElement(
                    index=element.get("index", 0),
                    text=element.get("text", ""),
                    resource_id=element.get("resource_id", ""),
                    content_desc=element.get("content_desc", ""),
                    bbox=element.get("bbox_normalized", {}),
                    clickable=element.get("clickable", False),
                    confidence=confidence
                ))
        
        # Sort by confidence
        found.sort(key=lambda x: x.confidence, reverse=True)
        return found
    
    def _matches_criteria(self, element: Dict, criteria: Dict) -> bool:
        """Check if element matches search criteria."""
        # Check text matching
        if "text" in criteria:
            text = element.get("text", "").lower()
            search_text = criteria["text"].lower()
            if search_text not in text:
                return False
        
        # Check resource_id matching
        if "resource_id" in criteria:
            resource_id = element.get("resource_id", "").lower()
            search_id = criteria["resource_id"].lower()
            if search_id not in resource_id:
                return False
        
        # Check content_desc matching
        if "content_desc" in criteria:
            content_desc = element.get("content_desc", "").lower()
            search_desc = criteria["content_desc"].lower()
            if search_desc not in content_desc:
                return False
        
        # Check clickable
        if "clickable" in criteria:
            if element.get("clickable", False) != criteria["clickable"]:
                return False
        
        return True
    
    def _calculate_confidence(self, element: Dict, criteria: Dict) -> float:
        """Calculate confidence score for match."""
        score = 0.0
        total_checks = 0
        
        if "text" in criteria:
            total_checks += 1
            text = element.get("text", "").lower()
            search_text = criteria["text"].lower()
            if text == search_text:
                score += 1.0
            elif search_text in text:
                score += 0.7
        
        if "resource_id" in criteria:
            total_checks += 1
            if criteria["resource_id"].lower() in element.get("resource_id", "").lower():
                score += 1.0
        
        if "content_desc" in criteria:
            total_checks += 1
            if criteria["content_desc"].lower() in element.get("content_desc", "").lower():
                score += 1.0
        
        if "clickable" in criteria:
            total_checks += 1
            if element.get("clickable", False) == criteria["clickable"]:
                score += 1.0
        
        return score / total_checks if total_checks > 0 else 0.0
    
    def find_app(self, app_name: str) -> Optional[FoundApp]:
        """Find an installed application."""
        apps = self.adapter.list_apps()
        
        for app in apps:
            package_name = app.get("package_name", "")
            name = app.get("name", "")
            
            if app_name.lower() in package_name.lower() or app_name.lower() in name.lower():
                return FoundApp(
                    package_name=package_name,
                    name=name,
                    installed=True
                )
        
        return None
    
    def search_screen(self, keyword: str) -> List[FoundElement]:
        """Search screen for elements containing keyword."""
        criteria = {
            "text": keyword,
            "clickable": True
        }
        return self.find_elements(criteria)
    
    def find_button(self, text: str) -> Optional[FoundElement]:
        """Find a button with specific text."""
        criteria = {
            "text": text,
            "clickable": True
        }
        return self.find_element(criteria)
    
    def find_input_field(self) -> Optional[FoundElement]:
        """Find an input field."""
        criteria = {
            "clickable": True
        }
        elements = self.find_elements(criteria)
        
        # Prioritize elements that look like input fields
        for element in elements:
            if any(keyword in element.resource_id.lower() for keyword in ["edit", "input", "text"]):
                return element
        
        return elements[0] if elements else None
