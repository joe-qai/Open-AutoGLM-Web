"""Reflector Agent - analyzes execution and provides feedback."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class Reflection:
    """Result of reflection."""
    analysis: str
    suggestions: List[str]
    confidence: float
    alternative_actions: List[Dict] = None


class ReflectorAgent:
    """Reflector Agent - analyzes execution failures and suggests improvements."""
    
    def __init__(self):
        self.reflection_history = []
    
    def reflect_on_failure(self, step: Dict, result: Dict) -> Reflection:
        """Analyze a failed step and provide reflection."""
        action = step.get("action", "")
        error = result.get("error", "")
        parameters = step.get("parameters", {})
        
        analysis = self._analyze_failure(action, error, parameters)
        suggestions = self._generate_suggestions(action, error, parameters)
        alternatives = self._generate_alternatives(action, parameters)
        
        reflection = Reflection(
            analysis=analysis,
            suggestions=suggestions,
            confidence=0.8,
            alternative_actions=alternatives
        )
        
        self.reflection_history.append({
            "step": step,
            "result": result,
            "reflection": reflection
        })
        
        return reflection
    
    def _analyze_failure(self, action: str, error: str, parameters: Dict) -> str:
        """Analyze the cause of failure."""
        if "No element found" in error:
            return f"Action '{action}' failed because no matching element was found. " \
                   "The target element may not be visible on screen, or the description " \
                   "may not match any element."
        
        if "crash" in error.lower():
            return f"Action '{action}' caused application crash. This indicates a " \
                   "potential compatibility issue or bug in the target application."
        
        if "timeout" in error.lower():
            return f"Action '{action}' timed out. The device may be unresponsive " \
                   "or the operation took too long to complete."
        
        if "not connected" in error.lower():
            return f"Action '{action}' failed because the device is not connected. " \
                   "Check device connection status."
        
        return f"Action '{action}' failed with error: {error}. The cause is not " \
               "immediately clear; further investigation is recommended."
    
    def _generate_suggestions(self, action: str, error: str, parameters: Dict) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        if "No element found" in error:
            suggestions.extend([
                "Check if the target element is visible on screen",
                "Try using different element identification criteria",
                "Consider waiting for the element to appear",
                "Verify the element description matches the actual UI"
            ])
        
        if "crash" in error.lower():
            suggestions.extend([
                "Check application logs for crash details",
                "Try a different approach to avoid triggering the crash",
                "Consider testing on a different device or OS version",
                "Report the crash to the application developer"
            ])
        
        if "timeout" in error.lower():
            suggestions.extend([
                "Increase timeout duration",
                "Check device responsiveness",
                "Break the action into smaller steps",
                "Add error handling for timeout cases"
            ])
        
        if not suggestions:
            suggestions.append("Review the action parameters and try again")
        
        return suggestions
    
    def _generate_alternatives(self, action: str, parameters: Dict) -> List[Dict]:
        """Generate alternative actions."""
        alternatives = []
        
        if action == "tap_element":
            alternatives.extend([
                {"action": "wait", "parameters": {"duration": 1000}},
                {"action": "swipe", "parameters": {"direction": "down"}},
                {"action": "long_press", "parameters": parameters}
            ])
        
        elif action == "type_text":
            alternatives.extend([
                {"action": "wait", "parameters": {"duration": 500}},
                {"action": "tap_element", "parameters": {"description": "搜索框"}}
            ])
        
        elif action == "swipe":
            alternatives.extend([
                {"action": "wait", "parameters": {"duration": 500}},
                {"action": "tap_element", "parameters": {"description": "下一页"}}
            ])
        
        return alternatives
    
    def reflect_on_complete_execution(self, history: List[Dict]) -> Reflection:
        """Reflect on entire execution history."""
        successes = sum(1 for h in history if h.get("success") is True)
        failures = sum(1 for h in history if h.get("success") is False)
        total_steps = len(history)
        
        analysis = f"Execution completed with {successes}/{total_steps} steps successful. " \
                   f"{failures} failures occurred."
        
        suggestions = []
        if failures > 0:
            suggestions.append("Review failed steps and consider alternative approaches")
            suggestions.append("Check device connectivity and responsiveness")
        
        suggestions.append("Consider optimizing successful steps for better performance")
        
        return Reflection(
            analysis=analysis,
            suggestions=suggestions,
            confidence=0.9
        )
