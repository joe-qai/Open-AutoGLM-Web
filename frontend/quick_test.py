from playwright.sync_api import sync_playwright
import os

os.makedirs('e2e_results', exist_ok=True)

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        print("测试1: 访问Dashboard...")
        page.goto('http://localhost:3000/')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)
        page.screenshot(path='e2e_results/01_dashboard.png', full_page=True)
        print("  Dashboard截图已保存")

        print("测试2: 导航到Agent页面...")
        try:
            page.locator('text=Agent脚本').click()
            page.wait_for_timeout(2000)
            page.screenshot(path='e2e_results/02_agent.png', full_page=True)
            print("  Agent页面截图已保存")
        except Exception as e:
            print(f"  错误: {e}")

        print("测试3: 导航到设备管理...")
        try:
            page.locator('text=设备管理').click()
            page.wait_for_timeout(2000)
            page.screenshot(path='e2e_results/03_devices.png', full_page=True)
            print("  设备管理截图已保存")
        except Exception as e:
            print(f"  错误: {e}")

        print("测试4: 导航到任务管理...")
        try:
            page.locator('text=任务管理').click()
            page.wait_for_timeout(2000)
            page.screenshot(path='e2e_results/04_tasks.png', full_page=True)
            print("  任务管理截图已保存")
        except Exception as e:
            print(f"  错误: {e}")

        print("测试5: 导航到脚本管理...")
        try:
            page.locator('text=脚本管理').click()
            page.wait_for_timeout(2000)
            page.screenshot(path='e2e_results/05_scripts.png', full_page=True)
            print("  脚本管理截图已保存")
        except Exception as e:
            print(f"  错误: {e}")

        print("测试6: 导航到设置...")
        try:
            page.locator('a:text("设置")').click()
            page.wait_for_timeout(2000)
            page.screenshot(path='e2e_results/06_settings.png', full_page=True)
            print("  设置截图已保存")
        except Exception as e:
            print(f"  错误: {e}")

        print("\n控制台日志:")
        errors = [log for log in console_logs if 'error' in log.lower()]
        if errors:
            for e in errors:
                print(f"  {e}")
        else:
            print("  无错误")

        browser.close()
        print("\n测试完成!")

if __name__ == "__main__":
    test()
