@echo off
setlocal DisableDelayedExpansion
set "OPLWU_SYSTEM1_BATCH_LAUNCH=1"
node "%~dp0configure-system1.mjs" %*
set "OPLWU_SYSTEM1_EXIT_CODE=%ERRORLEVEL%"
if "%OPLWU_SYSTEM1_EXIT_CODE%"=="9009" (
  echo System 1: Node.js 18+ is required and was not found on PATH.
  echo Install Node.js, then reopen this launcher. Use a terminal to inspect errors.
)
exit /b %OPLWU_SYSTEM1_EXIT_CODE%
