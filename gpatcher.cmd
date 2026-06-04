@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -m gpatcher %*
) else (
    powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_DIR%gpatcher.ps1" %*
)
