"""Agent Engine - coordinates all agents and layers."""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from ..adapters.factory import DeviceAdapterFactory
from ..adapters.base import Platform, BaseDeviceAdapter
from ..layers.perception import PerceptionLayer
from ..layers.decision import DecisionLayer, DecisionMode
from ..layers.action import ActionLayer
from ..layers.memory import MemoryLayer
from ..layers.verification import VerificationLayer
from ..layers.replay import ReplayLayer
from ..react_loop import ReActLoop
from ..ui_tree import UITreeExtractor
from ..element_locator import MultiStrategyElementLocator
from .manager import ManagerAgent, TaskPlan
from .executor import ExecutorAgent
from .reflector import ReflectorAgent
from .finder import FinderAgent


class AgentStatus(str, Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ExecutionStep:
    """Single step in execution."""

    step_index: int
    action: str
    parameters: Dict[str, Any]
    reasoning: str
    success: bool
    message: str
    perception_data: Optional[Dict] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionContext:
    """Context for current execution."""

    task_id: str
    task_description: str
    platform: Platform
    device: BaseDeviceAdapter
    steps_completed: int = 0
    max_steps: int = 100
    status: AgentStatus = AgentStatus.IDLE
    history: List[ExecutionStep] = field(default_factory=list)
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class AgentEngine:
    """Main engine that coordinates all agents and layers."""

    def __init__(self, mode: DecisionMode = DecisionMode.LLM):
        self.adapter: Optional[BaseDeviceAdapter] = None
        self.platform: Optional[Platform] = None
        self.mode = mode

        # Layers
        self.perception: Optional[PerceptionLayer] = None
        self.decision: Optional[DecisionLayer] = None
        self.action: Optional[ActionLayer] = None
        self.memory = MemoryLayer()
        self.verification = VerificationLayer()
        self.replay = ReplayLayer()

        # Agents
        self.manager = ManagerAgent()
        self.executor: Optional[ExecutorAgent] = None
        self.reflector = ReflectorAgent()
        self.finder: Optional[FinderAgent] = None

        # Execution context
        self.context: Optional[ExecutionContext] = None

        # Callbacks
        self.on_step: Optional[Callable[[ExecutionStep], None]] = None
        self.on_status_change: Optional[Callable[[AgentStatus], None]] = None

    def set_device(self, platform: Platform, **kwargs):
        """Set the target device."""
        self.platform = platform
        self.adapter = DeviceAdapterFactory.create_adapter(platform, **kwargs)

        # Initialize layers with adapter
        self.perception = PerceptionLayer(self.adapter)
        self.decision = DecisionLayer(mode=self.mode)
        self.action = ActionLayer(self.adapter)
        self.executor = ExecutorAgent(self.adapter)
        self.finder = FinderAgent(self.adapter)

        # Set up agent connections
        self.manager.set_executor(self.executor)
        self.manager.set_reflector(self.reflector)
        self.manager.set_finder(self.finder)

    def _update_status(self, status: AgentStatus):
        """Update execution status."""
        if self.context:
            self.context.status = status
        if self.on_status_change:
            self.on_status_change(status)

    def _execute_plan(self, plan: TaskPlan) -> Dict[str, Any]:
        """Execute a task plan step by step (legacy mode)."""
        results = []

        for step in plan.steps:
            if self.context and self.context.steps_completed >= self.context.max_steps:
                break

            # Record step
            self.replay.record_step(
                step_index=self.context.steps_completed if self.context else 0,
                action=step.get("action", ""),
                action_params=step.get("parameters", {}),
                thinking=step.get("description", ""),
            )

            # Execute step
            if self.executor:
                result = self.executor.execute_step(step)
                results.append(result)

            if self.context:
                self.context.history.append(result)
                self.context.steps_completed += 1

            # Check for completion
            if result.get("action") == "finish":
                break

            # Add delay between steps
            time.sleep(0.5)

        return {"results": results}

    async def _on_step_callback(self, data: dict):
        if self.memory:
            self.memory.add_memory(
                memory_type=f"step_{data.get('event', 'unknown')}",
                content=str(data),
            )

    async def execute_task(
        self,
        task_description: str,
        max_steps: int = 100,
        step_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using ReActLoop: Observe -> Think -> Act -> Reflect.

        Args:
            task_description: Natural language task description
            max_steps: Maximum steps to execute
            step_callback: Async callback for each executed step

        Returns:
            Execution result dictionary
        """
        if not self.adapter:
            return {"success": False, "error": "No device set"}

        self.on_step = step_callback

        self.context = ExecutionContext(
            task_id=f"task_{int(time.time())}",
            task_description=task_description,
            platform=self.platform,
            device=self.adapter,
            max_steps=max_steps,
            start_time=time.time(),
        )

        self.replay.start_recording(self.context.task_id)
        self._update_status(AgentStatus.RUNNING)

        react_loop = ReActLoop(
            ui_extractor=UITreeExtractor(self.adapter),
            llm_decider=self.decision,
            element_locator=MultiStrategyElementLocator(self.adapter),
            action_executor=self.action,
            max_iterations=max_steps,
            on_step=step_callback or self._on_step_callback,
        )

        try:
            result = await react_loop.run(
                task=task_description,
                task_id=self.context.task_id,
            )

            self.context.status = (
                AgentStatus.COMPLETED if result["success"] else AgentStatus.ERROR
            )
            self.context.end_time = time.time()
            self.context.steps_completed = result["total_steps"]

            if self.verification:
                v_result = self.verification.verify(result)
                result["verification"] = v_result

            replay_path = self.replay.stop_recording()
            result["replay_path"] = replay_path

            return result

        except Exception as e:
            self.context.status = AgentStatus.ERROR
            self.context.end_time = time.time()
            self.replay.stop_recording()
            return {
                "success": False,
                "total_steps": self.context.steps_completed if self.context else 0,
                "steps": [],
                "history": [],
                "final_message": f"执行异常: {e}",
            }

    def execute_step(self) -> Optional[Dict[str, Any]]:
        """Execute a single step in auto mode."""
        if not self.adapter or not self.context:
            return None

        if self.context.steps_completed >= self.context.max_steps:
            return {"action": "finish", "message": "Max steps reached"}

        try:
            # Perceive current state
            perception_data = self.perception.perceive_lightweight()

            # Make decision
            action_plan = self.decision.decide_simple(
                task=self.context.task_description,
                perception_data=perception_data,
                mode=self.mode,
            )

            # Execute action
            action_result = self.action.execute(action_plan)

            # Record to memory
            self.memory.add_memory(
                "action",
                {
                    "action": action_plan.action,
                    "reasoning": action_plan.reasoning,
                    "result": action_result.success,
                },
            )

            # Record to replay
            self.replay.record_step(
                step_index=self.context.steps_completed,
                action=action_plan.action,
                action_params=action_plan.parameters,
                thinking=action_plan.reasoning,
            )

            # Record step
            step = ExecutionStep(
                step_index=self.context.steps_completed,
                action=action_plan.action,
                parameters=action_plan.parameters,
                reasoning=action_plan.reasoning,
                success=action_result.success,
                message=action_result.message,
                perception_data=perception_data,
            )
            self.context.history.append(step)
            self.context.steps_completed += 1

            return {
                "step": step.step_index,
                "action": step.action,
                "parameters": step.parameters,
                "reasoning": step.reasoning,
                "success": step.success,
                "message": step.message,
                "perception": perception_data,
            }

        except Exception as e:
            return {"action": "error", "error": str(e)}

    def stop(self):
        """Stop current execution."""
        if self.context:
            self.context.status = AgentStatus.COMPLETED
            self.replay.stop_recording()

    def clear_memory(self):
        """Clear memory."""
        self.memory.clear_memory()
