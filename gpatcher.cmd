@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -m gpatcher %*
) else (
    echo [err] gpatcher requires Python to run. Please install Python and ensure it is in your PATH.
    exit /b 1
)
