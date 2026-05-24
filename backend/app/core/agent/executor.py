"""Executor Agent - executes individual steps."""

from typing import Dict, Any, Optional
import time

from ..layers.perception import PerceptionLayer
from ..layers.decision import DecisionLayer, ActionPlan
from ..layers.action import ActionLayer
from ..layers.memory import MemoryLayer


class ExecutorAgent:
    """Executor Agent - executes actions on device."""
    
    def __init__(self, adapter):
        self.perception = PerceptionLayer(adapter)
        self.decision = DecisionLayer()
        self.action = ActionLayer(adapter)
        self.memory = MemoryLayer()
        self.adapter = adapter
    
    def execute_step(self, step: Dict) -> Dict[str, Any]:
        """Execute a single step."""
        action_name = step.get("action", "")
        parameters = step.get("parameters", {})
        description = step.get("description", "")
        
        try:
            # Execute action based on type
            if action_name == "launch_app":
                result = self._execute_launch_app(parameters)
            elif action_name == "tap_element":
                result = self._execute_tap_element(parameters)
            elif action_name == "type_text":
                result = self._execute_type_text(parameters)
            elif action_name == "swipe":
                result = self._execute_swipe(parameters)
            elif action_name == "wait":
                result = self._execute_wait(parameters)
            elif action_name == "finish":
                result = self._execute_finish(parameters)
            elif action_name == "auto":
                # Auto mode: perceive -> decide -> act
                result = self._execute_auto_mode(description)
            else:
                result = {"success": False, "error": f"Unknown action: {action_name}"}
            
            # Store in memory
            self.memory.add_memory("action", {
                "action": action_name,
                "parameters": parameters,
                "result": result
            })
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "action": action_name,
                "error": str(e)
            }
    
    def _execute_launch_app(self, parameters: Dict) -> Dict:
        """Execute launch app action."""
        app_name = parameters.get("app_name", "")
        if not app_name:
            return {"success": False, "error": "No app name provided"}
        
        result = self.adapter.launch_app(app_name)
        time.sleep(2)  # Wait for app to launch
        
        return {
            "success": result,
            "action": "launch_app",
            "app_name": app_name,
            "message": f"Launched app: {app_name}"
        }
    
    def _execute_tap_element(self, parameters: Dict) -> Dict:
        """Execute tap element action."""
        if parameters.get("x") is not None and parameters.get("y") is not None:
            x, y = parameters["x"], parameters["y"]
            px, py = self.adapter.display_info.denormalize_coord(x, y)
            self.adapter.click(px, py)
            return {
                "success": True,
                "action": "tap_element",
                "position": {"x": x, "y": y},
                "message": f"Tapped at ({x}, {y})"
            }
        
        # Auto-detect and click
        perception = self.perception.perceive_lightweight()
        elements = perception.get("ui_elements", [])
        
        # Find clickable element based on description
        description = parameters.get("description", "")
        target_element = None
        for element in elements:
            if element.get("clickable") and (
                description in element.get("text", "") or
                description in element.get("content_desc", "")
            ):
                target_element = element
                break
        
        if target_element:
            self.adapter.click_element(target_element)
            return {
                "success": True,
                "action": "tap_element",
                "element": target_element,
                "message": f"Tapped element: {target_element.get('text', '')}"
            }
        
        return {"success": False, "error": "No element found"}
    
    def _execute_type_text(self, parameters: Dict) -> Dict:
        """Execute type text action."""
        text = parameters.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        
        result = self.adapter.type_text(text)
        return {
            "success": result,
            "action": "type_text",
            "text": text,
            "message": f"Typed: {text}"
        }
    
    def _execute_swipe(self, parameters: Dict) -> Dict:
        """Execute swipe action."""
        direction = parameters.get("direction", "down")
        
        # Default coordinates based on direction
        width, height = self.adapter.display_info.width, self.adapter.display_info.height
        
        swipe_map = {
            "up": (width // 2, height * 0.8, width // 2, height * 0.2),
            "down": (width // 2, height * 0.2, width // 2, height * 0.8),
            "left": (width * 0.8, height // 2, width * 0.2, height // 2),
            "right": (width * 0.2, height // 2, width * 0.8, height // 2),
        }
        
        x1, y1, x2, y2 = swipe_map.get(direction, swipe_map["down"])
        self.adapter.swipe(int(x1), int(y1), int(x2), int(y2))
        
        return {
            "success": True,
            "action": "swipe",
            "direction": direction,
            "message": f"Swiped {direction}"
        }
    
    def _execute_wait(self, parameters: Dict) -> Dict:
        """Execute wait action."""
        duration = parameters.get("duration", 1000)
        time.sleep(duration / 1000)
        
        return {
            "success": True,
            "action": "wait",
            "duration": duration,
            "message": f"Waited {duration}ms"
        }
    
    def _execute_finish(self, parameters: Dict) -> Dict:
        """Execute finish action."""
        message = parameters.get("message", "Task completed")
        return {
            "success": True,
            "action": "finish",
            "message": message
        }
    
    def _execute_auto_mode(self, description: str) -> Dict:
        """Execute in auto mode using VLM."""
        perception = self.perception.perceive_lightweight()
        
        # Make decision using VLM
        plan = self.decision.decide_simple(description, perception)
        
        # Execute the decided action
        result = self.action.execute(plan)
        
        return {
            "success": result.success,
            "action": plan.action,
            "reasoning": plan.reasoning,
            "message": result.message,
            "error": result.error
        }
