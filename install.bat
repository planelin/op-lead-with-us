@echo off
setlocal DisableDelayedExpansion
set "OPLWU_INSTALL_BATCH_LAUNCH=1"
node "%~dp0scripts\install-global.mjs" %*
set "OPLWU_INSTALL_EXIT_CODE=%ERRORLEVEL%"
if "%OPLWU_INSTALL_EXIT_CODE%"=="9009" (
  echo Installer: Node.js 18+ is required and was not found on PATH.
  echo 安装器需要 Node.js 18+，当前 PATH 中未找到 Node.js。
  pause
)
exit /b %OPLWU_INSTALL_EXIT_CODE%
