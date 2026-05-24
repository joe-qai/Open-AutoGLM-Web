@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

:: 设置颜色
color 0A

:: 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"

:: 检查虚拟环境是否存在
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo.
    echo ==================== 错误 ====================
    echo 虚拟环境不存在于: %VENV_DIR%
    echo 请先创建虚拟环境:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo ==============================================
    echo.
    pause
    exit /b 1
)

echo.
echo ==================== AutoPhone 启动脚本 ====================
echo.
echo 项目目录: %SCRIPT_DIR%
echo 虚拟环境: %VENV_DIR%
echo.

:: 激活虚拟环境并启动后端服务
echo [1/2] 启动后端服务...
start "AutoPhone Backend" cmd /k "cd /d %BACKEND_DIR% && call %VENV_DIR%\Scripts\activate.bat && echo 虚拟环境已激活: !VIRTUAL_ENV! && python run.py"

:: 等待后端启动（可选）
timeout /t 3 /nobreak >nul

:: 启动前端服务
echo [2/2] 启动前端服务...
start "AutoPhone Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm install && npm run dev"

echo.
echo ==================== 服务启动完成 ====================
echo.
echo 后端服务窗口: AutoPhone Backend
echo 前端服务窗口: AutoPhone Frontend
echo.
echo 前端访问地址: http://localhost:3000
echo 后端API地址: http://localhost:8000
echo.
echo 按任意键关闭此窗口...
pause >nul

endlocal