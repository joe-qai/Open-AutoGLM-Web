"""Script service for managing test scripts."""

from typing import List, Optional
import time
from datetime import datetime

from app.schemas.script import ScriptResponse, ScriptType


class ScriptService:
    """Service for script management."""
    
    def __init__(self):
        self.scripts = {}
        self.script_versions = {}
        # Initialize with some sample data
        self._init_sample_data()
    
    def _init_sample_data(self):
        """Initialize sample scripts for testing."""
        sample_scripts = [
            {
                "script_id": "script_1",
                "name": "微信登录测试",
                "content": "# Android 微信登录测试脚本\nimport uiautomator2 as u2\nimport time\n\nd = u2.connect()\n\n# 启动微信\nd.app_start(\"com.tencent.mm\")\ntime.sleep(3)\n\n# 执行登录操作\nprint(\"微信登录测试脚本执行中...\")\nprint(\"脚本执行完成\")",
                "script_type": "ai_generated",
                "platform": "android",
                "project_id": None,
                "description": "测试微信登录流程",
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:00:00",
                "version": 1
            },
            {
                "script_id": "script_2",
                "name": "设置应用测试",
                "content": "# Android 设置应用测试脚本\nimport uiautomator2 as u2\nimport time\n\nd = u2.connect()\n\n# 启动设置应用\nd.app_start(\"com.android.settings\")\ntime.sleep(2)\n\nprint(\"设置应用测试脚本执行中...\")\nprint(\"脚本执行完成\")",
                "script_type": "external",
                "platform": "android",
                "project_id": None,
                "description": "测试系统设置应用",
                "created_at": "2024-01-16T14:30:00",
                "updated_at": "2024-01-16T14:30:00",
                "version": 1
            },
            {
                "script_id": "script_3",
                "name": "iOS Safari测试",
                "content": "// iOS Safari 测试脚本\nimport XCTest\n\nclass SafariTest: XCTestCase {\n    var app: XCUIApplication!\n    \n    override func setUp() {\n        super.setUp()\n        app = XCUIApplication(bundleIdentifier: \"com.apple.mobilesafari\")\n        app.launch()\n    }\n    \n    func testOpenSafari() {\n        print(\"Safari 测试执行中...\")\n    }\n}",
                "script_type": "ai_generated",
                "platform": "ios",
                "project_id": None,
                "description": "测试iOS Safari浏览器",
                "created_at": "2024-01-17T09:00:00",
                "updated_at": "2024-01-17T09:00:00",
                "version": 1
            },
            {
                "script_id": "script_4",
                "name": "HarmonyOS 设置测试",
                "content": "// HarmonyOS 设置测试脚本\nimport ohos.hypium.Hypium;\nimport ohos.hypium.executor.Action;\nimport ohos.hypium.executor.Executor;\n\npublic class SettingsTest {\n    public static void main(String[] args) {\n        Executor executor = Hypium.createExecutor();\n        \n        try {\n            executor.execute(Action.launchApp(\"com.huawei.settings\"));\n            System.out.println(\"HarmonyOS 设置测试执行中...\");\n        } finally {\n            executor.release();\n        }\n    }\n}",
                "script_type": "external",
                "platform": "harmonyos",
                "project_id": None,
                "description": "测试HarmonyOS设置应用",
                "created_at": "2024-01-18T11:00:00",
                "updated_at": "2024-01-18T11:00:00",
                "version": 1
            }
        ]
        
        for script_data in sample_scripts:
            self.scripts[script_data["script_id"]] = script_data
    
    def create_script(
        self,
        name: str,
        content: str,
        script_type: str,
        platform: str,
        project_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Create a new script."""
        script_id = f"script_{int(time.time())}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        self.scripts[script_id] = {
            "script_id": script_id,
            "name": name,
            "content": content,
            "script_type": script_type,
            "platform": platform,
            "project_id": project_id,
            "description": description,
            "created_at": timestamp,
            "updated_at": timestamp,
            "version": 1
        }
        
        self._save_version(script_id, content, "Initial version")
        
        return script_id
    
    def get_script(self, script_id: str) -> Optional[ScriptResponse]:
        """Get script by ID."""
        script_data = self.scripts.get(script_id)
        if not script_data:
            return None
        
        return ScriptResponse(
            script_id=script_data["script_id"],
            name=script_data["name"],
            content=script_data["content"],
            script_type=ScriptType(script_data["script_type"]),
            platform=script_data["platform"],
            project_id=script_data.get("project_id"),
            description=script_data.get("description"),
            created_at=script_data["created_at"],
            updated_at=script_data.get("updated_at"),
            version=script_data.get("version", 1)
        )
    
    def update_script(self, script_id: str, update):
        """Update a script."""
        script_data = self.scripts.get(script_id)
        if not script_data:
            return
        
        if update.name is not None:
            script_data["name"] = update.name
        if update.content is not None:
            script_data["content"] = update.content
            script_data["version"] = script_data.get("version", 1) + 1
        if update.description is not None:
            script_data["description"] = update.description
        
        script_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    
    def delete_script(self, script_id: str):
        """Delete a script."""
        if script_id in self.scripts:
            del self.scripts[script_id]
        if script_id in self.script_versions:
            del self.script_versions[script_id]
    
    def list_scripts(
        self,
        project_id: str | None = None,
        script_type: ScriptType | None = None,
        platform: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScriptResponse]:
        """List all scripts."""
        script_list = []
        
        for script_data in self.scripts.values():
            if project_id and script_data["project_id"] != project_id:
                continue
            if script_type and script_data["script_type"] != script_type.value:
                continue
            if platform and script_data["platform"] != platform:
                continue
            
            script_list.append(ScriptResponse(
                script_id=script_data["script_id"],
                name=script_data["name"],
                content=script_data["content"],
                script_type=ScriptType(script_data["script_type"]),
                platform=script_data["platform"],
                project_id=script_data.get("project_id"),
                description=script_data.get("description"),
                created_at=script_data["created_at"],
                updated_at=script_data.get("updated_at"),
                version=script_data.get("version", 1)
            ))
        
        return script_list[skip:skip + limit]
    
    def execute_script(self, script_id: str, device_id: str = None) -> str:
        """Execute a script by creating a task and delegating to TaskService.
        Returns the task_id of the created task."""
        from app.services.task_service import TaskService

        script = self.get_script(script_id)
        if not script:
            return ""

        task_service = TaskService()
        task_id = task_service.create_task(
            name=f"Execute: {script.name}",
            description=f"Script execution: {script.name}",
            script_id=script_id,
            device_id=device_id,
            platform=script.platform,
        )

        # Execute the task via the agent engine
        task_service.execute_task(task_id)

        return task_id

    def generate_script(self, task_description: str, platform: str, project_id: Optional[str] = None) -> str:
        """Generate a script from task description."""
        script_content = self._generate_script_content(task_description, platform)
        
        return self.create_script(
            name=f"Generated Script - {task_description[:30]}",
            content=script_content,
            script_type="ai_generated",
            platform=platform,
            project_id=project_id,
            description=f"Auto-generated script for: {task_description}"
        )
    
    def _generate_script_content(self, task_description: str, platform: str) -> str:
        """Generate script content based on platform."""
        timestamp = datetime.now().isoformat()
        
        if platform == "android":
            return f'''# Android 脚本 (Python + uiautomator2)
# 生成时间: {timestamp}
# 任务: {task_description}

import uiautomator2 as u2
import time

# 连接设备
d = u2.connect()

try:
    # TODO: 根据任务描述实现自动化步骤
    # {task_description}
    
    # 示例步骤:
    # 1. 启动应用
    # d.app_start("com.example.app")
    
    # 2. 点击操作
    # d.click(x, y)
    
    # 3. 输入文本
    # d.send_keys("文本内容")
    
    # 4. 滑动操作
    # d.swipe(start_x, start_y, end_x, end_y)
    
    print("脚本执行完成")

finally:
    pass
'''
        elif platform == "ios":
            return f'''// iOS 脚本 (XCTest)
// 生成时间: {timestamp}
// 任务: {task_description}

import XCTest

class GeneratedTest: XCTestCase {{
    var app: XCUIApplication!
    
    override func setUp() {{
        super.setUp()
        app = XCUIApplication()
        app.launch()
    }}
    
    func testTask() {{
        // TODO: 根据任务描述实现自动化步骤
        // {task_description}
        
        // 示例步骤:
        // app.buttons["按钮"].tap()
        // app.textFields["输入框"].typeText("文本")
        // app.swipeUp()
    }}
}}
'''
        elif platform == "harmonyos":
            return f'''// HarmonyOS 脚本 (Hypium)
// 生成时间: {timestamp}
// 任务: {task_description}

import ohos.hypium.Hypium;
import ohos.hypium.executor.Action;
import ohos.hypium.executor.Executor;

public class GeneratedTest {{
    public static void main(String[] args) {{
        Executor executor = Hypium.createExecutor();
        
        try {{
            // TODO: 根据任务描述实现自动化步骤
            // {task_description}
            
            // 示例步骤:
            // executor.execute(Action.launchApp("com.example.app"));
            // executor.execute(Action.clickById("button_id"));
            // executor.execute(Action.inputText("edit_text_id", "文本"));
            
        }} finally {{
            executor.release();
        }}
    }}
}}
'''
        else:
            return f'''# 通用脚本
# 生成时间: {timestamp}
# 任务: {task_description}
# 平台: {platform}

# TODO: 实现自动化步骤
'''
    
    def derive_script(self, script_id: str, platform: str) -> str:
        """Derive a script for a different platform."""
        original_script = self.get_script(script_id)
        if not original_script:
            return ""
        
        new_content = self._generate_script_content(
            original_script.description or original_script.name,
            platform
        )
        
        return self.create_script(
            name=f"{original_script.name} ({platform})",
            content=new_content,
            script_type="ai_generated",
            platform=platform,
            project_id=original_script.project_id,
            description=f"Derived from {script_id}"
        )
    
    def _save_version(self, script_id: str, content: str, comment: str = ""):
        """Save a version of the script."""
        if script_id not in self.script_versions:
            self.script_versions[script_id] = []
        
        version_number = len(self.script_versions[script_id]) + 1
        
        self.script_versions[script_id].append({
            "version_id": f"v{version_number}",
            "script_id": script_id,
            "content": content,
            "version_number": version_number,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "comment": comment
        })
    
    def save_script_version(self, script_id: str, content: str, comment: str = "") -> str:
        """Save a new version of the script."""
        self._save_version(script_id, content, comment)
        
        if script_id in self.scripts:
            self.scripts[script_id]["content"] = content
            self.scripts[script_id]["version"] = self.scripts[script_id].get("version", 1) + 1
            self.scripts[script_id]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        
        return f"v{len(self.script_versions[script_id])}"
    
    def get_script_versions(self, script_id: str) -> List[dict]:
        """Get version history of a script."""
        return self.script_versions.get(script_id, [])