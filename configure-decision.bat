@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "SCRIPT_DIR=%~dp0"
set "PY_EXE="

for /d %%D in ("%LOCALAPPDATA%\antigravity\python\*") do (
  if exist "%%~D\python.exe" (
    set "PY_EXE=%%~D\python.exe"
  )
)

if not defined PY_EXE (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PY_EXE=python"
  )
)

if not defined PY_EXE (
  echo [ERROR] Python runtime not found ^(Antigravity bundled python or python on PATH^).
  if "%~1"=="" pause
  exit /b 1
)

"%PY_EXE%" "%SCRIPT_DIR%scripts\configure-decision.py" %*
set "EXIT_CODE=%ERRORLEVEL%"

if "%~1"=="" (
  if not "%EXIT_CODE%"=="0" pause
)
exit /b %EXIT_CODE%