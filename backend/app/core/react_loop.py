from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any, Callable
from datetime import datetime
import asyncio


@dataclass
class ReActStep:
    step_index: int
    phase: Literal["observe", "think", "act", "reflect"]
    ui_state: str = ""
    thought: str = ""
    action: str = ""
    action_params: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    success: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class ReActLoop:
    def __init__(
        self,
        ui_extractor,
        llm_decider,
        element_locator,
        action_executor,
        max_iterations: int = 50,
        on_step: Optional[Callable] = None,
    ):
        self.ui_extractor = ui_extractor
        self.llm_decider = llm_decider
        self.element_locator = element_locator
        self.action_executor = action_executor
        self.max_iterations = max_iterations
        self.on_step = on_step

    async def run(self, task: str, task_id: str = None) -> dict:
        history = []
        steps_log = []

        for iteration in range(self.max_iterations):
            step = ReActStep(step_index=iteration + 1, phase="observe")
            try:
                ui_tree_xml = self.ui_extractor.extract()
                ui_text = self.ui_extractor.to_text(ui_tree_xml)
            except Exception:
                ui_text = "[UI 提取失败]"
            step.ui_state = ui_text

            await self._emit(
                "observe",
                step,
                task_id,
                {
                    "ui_summary": ui_text[:200] if len(ui_text) > 200 else ui_text,
                },
            )

            step.phase = "think"
            try:
                plan = await asyncio.to_thread(
                    self.llm_decider.decide,
                    task=task,
                    ui_text=ui_text,
                    history=history,
                )
            except Exception:
                step.thought = "[LLM 决策失败]"
                step.action = "wait"
                step.action_params = {"duration": 1}
                step.success = False
                await self._emit(
                    "think",
                    step,
                    task_id,
                    {
                        "thought": step.thought,
                        "proposed_action": step.action,
                    },
                )
                steps_log.append(step)
                await asyncio.sleep(1.5)
                continue

            step.thought = plan.reasoning
            step.action = plan.action
            step.action_params = plan.parameters

            await self._emit(
                "think",
                step,
                task_id,
                {
                    "thought": plan.reasoning,
                    "proposed_action": plan.action,
                    "params": plan.parameters,
                },
            )

            step.phase = "act"

            if plan.action == "finish":
                step.result = plan.parameters.get("message", "任务完成")
                step.success = True
                steps_log.append(step)
                await self._emit(
                    "act",
                    step,
                    task_id,
                    {
                        "action": "finish",
                        "message": step.result,
                    },
                )
                break

            locator_type = plan.parameters.get("locator_type")
            locator_value = plan.parameters.get("locator_value")
            target_coords = None

            if locator_type and locator_value:
                from .element_locator import ElementLocator, LocatorType

                try:
                    lt = LocatorType(locator_type)
                    locator = ElementLocator(
                        locator_type=lt,
                        value=locator_value,
                        index=plan.parameters.get("locator_index", 0),
                    )
                    result = self.element_locator.locate(locator)
                    if result.success:
                        target_coords = (result.x, result.y)
                except Exception:
                    pass

            if target_coords is None:
                fb = plan.parameters.get("fallback_coords")
                if fb and len(fb) == 2:
                    target_coords = (fb[0], fb[1])

            if target_coords:
                plan.parameters["x"] = target_coords[0]
                plan.parameters["y"] = target_coords[1]

            try:
                action_result = await asyncio.to_thread(
                    self.action_executor.execute, plan
                )
                step.result = action_result.message
                step.success = action_result.success
            except Exception:
                step.result = "[执行失败]"
                step.success = False

            await self._emit(
                "act",
                step,
                task_id,
                {
                    "action": plan.action,
                    "params": plan.parameters,
                    "target_coords": target_coords,
                    "result": step.result,
                    "success": step.success,
                },
            )

            step.phase = "reflect"
            if not step.success:
                step.thought += f"\n[反思] 执行失败: {step.result}"
                if target_coords is None:
                    step.thought += " (元素未定位到)"

            history.append(
                {
                    "step": iteration + 1,
                    "action": step.action,
                    "params": step.action_params,
                    "result": step.result,
                    "success": step.success,
                }
            )
            steps_log.append(step)

            await self._emit(
                "reflect",
                step,
                task_id,
                {
                    "reflection": step.thought,
                    "history_summary": f"已完成 {len(history)} 步，成功 {sum(1 for h in history if h['success'])} 步",
                },
            )

            await asyncio.sleep(1.5)

        final_step = (
            steps_log[-1]
            if steps_log
            else ReActStep(step_index=0, phase="reflect", success=False)
        )
        return {
            "success": final_step.success,
            "total_steps": len(steps_log),
            "steps": [
                {
                    "step_index": s.step_index,
                    "phase": s.phase,
                    "action": s.action,
                    "params": s.action_params,
                    "result": s.result,
                    "success": s.success,
                    "thought": s.thought,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in steps_log
            ],
            "history": history,
            "final_message": (
                final_step.result
                if final_step.success
                else f"达到最大迭代次数 ({self.max_iterations})"
            ),
        }

    async def _emit(
        self, phase: str, step: ReActStep, task_id: str = None, extra: dict = None
    ):
        if not self.on_step:
            return
        data = {
            "task_id": task_id,
            "event": phase,
            "step": step.step_index,
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            data.update(extra)
        try:
            await self.on_step(data)
        except Exception:
            pass
