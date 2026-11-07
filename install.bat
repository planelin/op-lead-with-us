@echo off
setlocal EnableExtensions
chcp 65001 >nul
title op-lead-with-us installer
cd /d "%~dp0"

echo ==================================================
echo   op-lead-with-us - quick installer
echo   Antigravity multi-model orchestration plugin
echo ==================================================
echo.

if /i "%~1"=="help" goto :usage
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="--help" goto :usage

rem --- Node.js presence check ---
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found in PATH.
    echo         Install Node.js 18 or later from https://nodejs.org and re-run this file.
    echo.
    pause
    exit /b 1
)

rem --- Node.js major version check (requires >= 18) ---
set "NODE_VER="
set "NODE_MAJOR="
for /f "usebackq delims=" %%v in (`node -v`) do set "NODE_VER=%%v"
set "NODE_VER=%NODE_VER:v=%"
for /f "delims=. tokens=1" %%m in ("%NODE_VER%") do set "NODE_MAJOR=%%m"
if not defined NODE_MAJOR (
    echo [ERROR] Could not determine the Node.js version from "node -v".
    pause
    exit /b 1
)
if %NODE_MAJOR% LSS 18 (
    echo [ERROR] Node.js %NODE_VER% is too old. This installer requires Node.js 18+.
    echo         Please upgrade from https://nodejs.org and re-run this file.
    echo.
    pause
    exit /b 1
)
echo [OK] Node.js %NODE_VER% detected.
echo.

rem --- Run installer / uninstaller ---
if /i "%~1"=="uninstall" goto :uninstall
if /i "%~1"=="-u" goto :uninstall

echo Running: node scripts\install-global.mjs
echo --------------------------------------------------
node scripts\install-global.mjs
if errorlevel 1 (
    echo.
    echo [FAIL] Installation failed. Fix the problem above and re-run this file.
    echo.
    pause
    exit /b 1
)
echo.
echo [DONE] Installed. Restart Antigravity or open a new conversation (Ctrl+N),
echo        then pick the agent from the Agent selector:
echo          - op-lead-with-us  : save main-model quota (Opus recommended)
echo          - op-lead-with-cry : Turbo concurrent mode (Flash recommended)
echo.
goto :end

:uninstall
echo Running: node scripts\install-global.mjs --uninstall
echo --------------------------------------------------
node scripts\install-global.mjs --uninstall
if errorlevel 1 (
    echo.
    echo [FAIL] Uninstallation failed. See the output above.
    echo.
    pause
    exit /b 1
)
echo.
goto :end

:usage
echo Usage:
echo   install.bat              install the plugin globally for Antigravity
echo   install.bat uninstall    remove the global installation
echo   install.bat help         show this help
echo.

:end
pause
endlocal
