@echo off
setlocal enabledelayedexpansion
echo ==============================================
echo           批量杀端口脚本
echo ==============================================

set "PORTS=8005 3000"
set "TARGET_STATE=LISTENING"

for %%p in (%PORTS%) do (
    echo.
    echo 正在处理端口: %%p
    
    set "found_pid="
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr ":%%p" ^| findstr "%TARGET_STATE%"') do (
        if not "!found_pid!"=="%%i" (
            set "found_pid=%%i"
            echo   找到 %TARGET_STATE% 进程 PID: %%i
            taskkill /F /PID %%i
            if !errorlevel! equ 0 (
                echo   成功终止进程 %%i
            ) else (
                echo   终止进程 %%i 失败
            )
        )
    )
    
    if not defined found_pid (
        echo   未找到 %TARGET_STATE% 状态的进程
    )
)

echo.
echo ==============================================
echo 处理完成！
echo ==============================================
pause