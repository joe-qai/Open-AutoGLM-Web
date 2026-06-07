@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

color 0A

set "SCRIPT_DIR=%~dp0"
set "VENV_NAME=mcp311"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"
set "KILL_SCRIPT=%SCRIPT_DIR%kill_ports.bat"

echo.
echo ==================== AutoPhone Start Script (mcp311) ====================
echo.
echo Project: %SCRIPT_DIR%
echo VENV: %VENV_NAME%
echo.

echo [0/3] Stopping existing services...
if exist "%KILL_SCRIPT%" (
    call "%KILL_SCRIPT%"
) else (
    echo kill_ports.bat not found, skip port cleanup
)
echo.

echo [1/3] Starting backend...
start "AutoPhone Backend" cmd /k "cd /d %BACKEND_DIR% && call activate %VENV_NAME% && echo VENV activated: %VENV_NAME% && python run.py"

timeout /t 3 /nobreak >nul

echo [2/3] Starting frontend...
start "AutoPhone Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

echo.
echo [3/3] Done!
echo.
echo ==================== Services Started ====================
echo.
echo Backend: AutoPhone Backend
echo Frontend: AutoPhone Frontend
echo.
echo Frontend URL: http://localhost:3000
echo Backend API: http://localhost:8005
echo.
echo Press any key to close...
pause >nul

endlocal
