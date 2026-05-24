from typing import List, Dict, Any


class ScriptGenerator:
    def generate(
        self, steps: List[Dict[str, Any]], task_info: Dict[str, Any] = None
    ) -> str:
        task_info = task_info or {}
        device_serial = task_info.get("device_serial", "emulator-5554")
        task_desc = task_info.get("task_description", "auto_task")

        lines = []
        lines.append('"""')
        lines.append(f"Auto-generated test: {task_desc}")
        lines.append(f"Generated at: {__import__('datetime').datetime.now()}")
        lines.append('"""')
        lines.append("")
        lines.append("import uiautomator2 as u2")
        lines.append("import time")
        lines.append("")
        lines.append(f"def test_{self._sanitize_name(task_desc)}():")
        lines.append(f'    d = u2.connect("{device_serial}")')
        lines.append("")

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = step.get("params", {})
            result = step.get("result", "")
            indent = "    "

            if action == "launch":
                app = params.get("app", "")
                lines.append(f"{indent}# Step {i + 1}: 启动 {app}")
                lines.append(f'{indent}d.app_start("{app}")')
                lines.append(f"{indent}time.sleep(2)")

            elif action == "tap":
                x = params.get("x", 0)
                y = params.get("y", 0)
                locator_type = params.get("locator_type", "")
                locator_value = params.get("locator_value", "")

                lines.append(f"{indent}# Step {i + 1}: 点击")
                if locator_type == "text":
                    lines.append(f'{indent}element = d(text="{locator_value}")')
                    lines.append(
                        f"{indent}assert element.exists, '元素未找到: {locator_value}'"
                    )
                    lines.append(f"{indent}element.click()")
                elif locator_type == "text_contains":
                    lines.append(f'{indent}element = d(textContains="{locator_value}")')
                    lines.append(
                        f"{indent}assert element.exists, '元素未找到: {locator_value}'"
                    )
                    lines.append(f"{indent}element.click()")
                elif locator_type == "resource_id":
                    lines.append(f'{indent}element = d(resourceId="{locator_value}")')
                    lines.append(
                        f"{indent}assert element.exists, '元素未找到: {locator_value}'"
                    )
                    lines.append(f"{indent}element.click()")
                else:
                    lines.append(f"{indent}d.click({x}, {y})")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "type":
                text = params.get("text", "")
                lines.append(f"{indent}# Step {i + 1}: 输入文本")
                lines.append(f'{indent}d.send_keys("{self._escape(text)}")')
                lines.append(f"{indent}time.sleep(1)")

            elif action == "swipe":
                sx = params.get("start_x", 0) or params.get("x", 0)
                sy = params.get("start_y", 0) or params.get("y", 0)
                ex = params.get("end_x", 0)
                ey = params.get("end_y", 0)
                lines.append(f"{indent}# Step {i + 1}: 滑动")
                lines.append(f"{indent}d.swipe({sx}, {sy}, {ex}, {ey})")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "back":
                lines.append(f"{indent}# Step {i + 1}: 返回")
                lines.append(f"{indent}d.press('back')")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "home":
                lines.append(f"{indent}# Step {i + 1}: 回到桌面")
                lines.append(f"{indent}d.press('home')")
                lines.append(f"{indent}time.sleep(1)")

            elif action == "wait":
                duration = params.get("duration", 1)
                lines.append(f"{indent}# Step {i + 1}: 等待 {duration}s")
                lines.append(f"{indent}time.sleep({duration})")

            elif action == "finish":
                message = params.get("message", "完成")
                lines.append(f"{indent}# Step {i + 1}: 完成 - {message}")

            if result:
                lines.append(f"{indent}# 结果: {result}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _sanitize_name(name: str) -> str:
        import re

        sanitized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff_]", "_", name)
        if not sanitized:
            sanitized = "auto_task"
        return sanitized[:50]

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace('"', '\\"')
