"""Manager Agent - orchestrates task planning and coordination."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class TaskPhase(str, Enum):
    """Phases of task execution."""
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"


@dataclass
class TaskPlan:
    """Plan for task execution."""
    task_id: str
    description: str
    platform: str
    devices: List[str]
    steps: List[Dict] = field(default_factory=list)
    phase: TaskPhase = TaskPhase.PLANNING
    estimated_steps: int = 0


class ManagerAgent:
    """Manager Agent - plans and coordinates task execution."""
    
    def __init__(self):
        self.executor = None
        self.reflector = None
        self.finder = None
    
    def set_executor(self, executor):
        """Set executor agent."""
        self.executor = executor
    
    def set_reflector(self, reflector):
        """Set reflector agent."""
        self.reflector = reflector
    
    def set_finder(self, finder):
        """Set finder agent."""
        self.finder = finder
    
    def plan_task(self, task_description: str, platform: str, devices: List[str]) -> TaskPlan:
        """Create a plan for executing a task."""
        plan = TaskPlan(
            task_id=f"task_{int(time.time())}",
            description=task_description,
            platform=platform,
            devices=devices,
            phase=TaskPhase.PLANNING
        )
        
        # Analyze task and create initial steps
        plan.steps = self._analyze_and_plan(task_description, platform)
        plan.estimated_steps = len(plan.steps)
        
        return plan
    
    def _analyze_and_plan(self, task_description: str, platform: str) -> List[Dict]:
        """Analyze task and generate execution steps."""
        steps = []
        
        # Simple heuristic-based planning
        if "打开" in task_description or "启动" in task_description:
            app_name = self._extract_app_name(task_description)
            if app_name:
                steps.append({
                    "action": "launch_app",
                    "parameters": {"app_name": app_name},
                    "description": f"启动应用: {app_name}"
                })
        
        if "点击" in task_description:
            steps.append({
                "action": "tap_element",
                "parameters": {"description": "根据屏幕内容识别目标元素"},
                "description": "点击目标元素"
            })
        
        if "搜索" in task_description:
            steps.append({
                "action": "type_text",
                "parameters": {"text": self._extract_search_query(task_description)},
                "description": "输入搜索内容"
            })
        
        if "滑动" in task_description or "滚动" in task_description:
            steps.append({
                "action": "swipe",
                "parameters": {"direction": "down"},
                "description": "向下滑动屏幕"
            })
        
        steps.append({
            "action": "finish",
            "parameters": {"message": "任务完成"},
            "description": "完成任务"
        })
        
        return steps
    
    def _extract_app_name(self, task_description: str) -> Optional[str]:
        """Extract app name from task description."""
        app_keywords = ["微信", "小红书", "抖音", "淘宝", "支付宝", "微博"]
        for keyword in app_keywords:
            if keyword in task_description:
                return self._get_app_package(keyword)
        return None
    
    def _get_app_package(self, app_name: str) -> str:
        """Get package name for app."""
        app_map = {
            "微信": "com.tencent.mm",
            "小红书": "com.xingin.xhs",
            "抖音": "com.ss.android.ugc.aweme",
            "淘宝": "com.taobao.taobao",
            "支付宝": "com.eg.android.AlipayGphone",
            "微博": "com.sina.weibo"
        }
        return app_map.get(app_name, app_name)
    
    def _extract_search_query(self, task_description: str) -> str:
        """Extract search query from task description."""
        if "搜索" in task_description:
            parts = task_description.split("搜索")
            if len(parts) > 1:
                return parts[1].strip()
        return ""
    
    def execute_plan(self, plan: TaskPlan) -> Dict[str, Any]:
        """Execute a task plan."""
        plan.phase = TaskPhase.EXECUTING
        
        execution_results = []
        for step in plan.steps:
            if self.executor:
                result = self.executor.execute_step(step)
                execution_results.append(result)
                
                if result.get("success") is False:
                    # Call reflector to analyze failure
                    if self.reflector:
                        reflection = self.reflector.reflect_on_failure(step, result)
                        execution_results.append({"reflection": reflection})
                    
                    break
        
        plan.phase = TaskPhase.COMPLETED
        
        return {
            "plan": plan,
            "results": execution_results,
            "summary": self._generate_summary(execution_results)
        }
    
    def _generate_summary(self, results: List[Dict]) -> str:
        """Generate summary of execution."""
        success_count = sum(1 for r in results if r.get("success") is True)
        total_steps = len([r for r in results if "action" in r])
        
        return f"执行完成: {success_count}/{total_steps} 步骤成功"
