from playwright.sync_api import sync_playwright
import time

def test_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("=== 1. 导航到Dashboard ===")
        page.goto('http://localhost:3000/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/e2e_results/01_dashboard.png', full_page=True)
        print(f"Dashboard截图已保存")

        print("\n=== 2. 检查页面标题和基本元素 ===")
        title = page.title()
        print(f"页面标题: {title}")

        sidebar = page.locator('aside')
        if sidebar.is_visible():
            print("侧边栏可见")
        else:
            print("侧边栏不可见")

        header = page.locator('header')
        if header.is_visible():
            print("顶部导航栏可见")
        else:
            print("顶部导航栏不可见")

        print("\n=== 3. 导航到Agent页面 ===")
        agent_link = page.locator('text=Agent脚本')
        if agent_link.is_visible():
            agent_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/02_agent/02_agent_page.png', full_page=True)
            print("Agent页面截图已保存")
        else:
            print("Agent脚本链接未找到")

        print("\n=== 4. 导航到设备管理页面 ===")
        devices_link = page.locator('text=设备管理')
        if devices_link.is_visible():
            devices_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/03_devices/03_devices_page.png', full_page=True)
            print("设备管理页面截图已保存")
        else:
            print("设备管理链接未找到")

        print("\n=== 5. 导航到任务管理页面 ===")
        tasks_link = page.locator('text=任务管理')
        if tasks_link.is_visible():
            tasks_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/04_tasks/04_tasks_page.png', full_page=True)
            print("任务管理页面截图已保存")
        else:
            print("任务管理链接未找到")

        print("\n=== 6. 导航到脚本管理页面 ===")
        scripts_link = page.locator('text=脚本管理')
        if scripts_link.is_visible():
            scripts_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/05_scripts/05_scripts_page.png', full_page=True)
            print("脚本管理页面截图已保存")
        else:
            print("脚本管理链接未找到")

        print("\n=== 7. 导航到系统设置页面 ===")
        settings_link = page.locator('text=设置')
        if settings_link.is_visible():
            settings_link.click()
            page.wait_for_timeout(2000)
            page.screenshot(path='c:/pythonworkspace/Open-AutoPhone/frontend/06_settings/06_settings_page.png', full_page=True)
            print("系统设置页面截图已保存")
        else:
            print("系统设置链接未找到")

        print("\n=== 控制台日志 ===")
        error_count = 0
        for log in console_logs:
            if '[error]' in log.lower() or '[warning]' in log.lower():
                print(log)
                if '[error]' in log.lower():
                    error_count += 1

        if error_count == 0:
            print("没有控制台错误")
        else:
            print(f"发现 {error_count} 个控制台错误")

        browser.close()
        print("\n=== E2E测试完成 ===")

if __name__ == "__main__":
    test_frontend()

