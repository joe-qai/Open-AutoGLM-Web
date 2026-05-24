"""Replay layer for the Agent architecture."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
import os
import time


@dataclass
class ReplayStep:
    """Single step in replay."""
    step_index: int
    timestamp: float
    action: str
    action_params: Dict[str, Any]
    screenshot_path: Optional[str] = None
    ui_elements: Optional[List[Dict]] = None
    thinking: Optional[str] = None


class ReplayLayer:
    """Replay layer - records and replays task execution."""
    
    def __init__(self, replay_dir: str = "./replays"):
        self.replay_dir = replay_dir
        self.current_replay: List[ReplayStep] = []
        self.is_recording = False
        os.makedirs(replay_dir, exist_ok=True)
    
    def start_recording(self, task_id: str):
        """Start recording a new replay."""
        self.current_replay = []
        self.current_task_id = task_id
        self.is_recording = True
        self.start_time = time.time()
    
    def record_step(
        self,
        step_index: int,
        action: str,
        action_params: Dict[str, Any],
        screenshot_path: Optional[str] = None,
        ui_elements: Optional[List[Dict]] = None,
        thinking: Optional[str] = None
    ):
        """Record a single step."""
        if not self.is_recording:
            return
        
        step = ReplayStep(
            step_index=step_index,
            timestamp=time.time(),
            action=action,
            action_params=action_params,
            screenshot_path=screenshot_path,
            ui_elements=ui_elements,
            thinking=thinking
        )
        self.current_replay.append(step)
    
    def stop_recording(self) -> str:
        """Stop recording and save replay."""
        self.is_recording = False
        
        if not self.current_replay:
            return ""
        
        replay_data = {
            "task_id": self.current_task_id,
            "start_time": self.start_time,
            "end_time": time.time(),
            "steps": [
                {
                    "step_index": step.step_index,
                    "timestamp": step.timestamp,
                    "action": step.action,
                    "action_params": step.action_params,
                    "screenshot_path": step.screenshot_path,
                    "thinking": step.thinking
                }
                for step in self.current_replay
            ]
        }
        
        filename = f"replay_{self.current_task_id}_{int(time.time())}.json"
        filepath = os.path.join(self.replay_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(replay_data, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def load_replay(self, replay_path: str) -> Optional[List[ReplayStep]]:
        """Load a saved replay."""
        if not os.path.exists(replay_path):
            return None
        
        with open(replay_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        steps = []
        for step_data in data.get("steps", []):
            step = ReplayStep(
                step_index=step_data["step_index"],
                timestamp=step_data["timestamp"],
                action=step_data["action"],
                action_params=step_data["action_params"],
                screenshot_path=step_data.get("screenshot_path"),
                thinking=step_data.get("thinking")
            )
            steps.append(step)
        
        return steps
    
    def list_replays(self) -> List[Dict[str, Any]]:
        """List all saved replays."""
        replays = []
        
        for file in os.listdir(self.replay_dir):
            if file.startswith("replay_") and file.endswith(".json"):
                filepath = os.path.join(self.replay_dir, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    replays.append({
                        "filename": file,
                        "task_id": data.get("task_id"),
                        "start_time": data.get("start_time"),
                        "end_time": data.get("end_time"),
                        "step_count": len(data.get("steps", []))
                    })
                except Exception:
                    pass
        
        return sorted(replays, key=lambda x: x["start_time"], reverse=True)
    
    def get_replay_summary(self, replay_path: str) -> Optional[Dict[str, Any]]:
        """Get summary of a replay."""
        steps = self.load_replay(replay_path)
        if not steps:
            return None
        
        actions = [step.action for step in steps]
        action_counts = {}
        for action in actions:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "step_count": len(steps),
            "duration": steps[-1].timestamp - steps[0].timestamp if steps else 0,
            "action_counts": action_counts,
            "first_action": steps[0].action if steps else None,
            "last_action": steps[-1].action if steps else None
        }
