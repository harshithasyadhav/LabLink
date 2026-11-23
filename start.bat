@echo off
title LabLink - Campus Laboratory Resource Platform
echo ======================================================================
echo    Starting LabLink Platform on local environment...
echo ======================================================================

where python >nul 2>&1
if %errorlevel% equ 0 (
    python run.py
    goto end
)

where py >nul 2>&1
if %errorlevel% equ 0 (
    py run.py
    goto end
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" run.py
    goto end
)

echo [ERROR] Python not found in PATH.
echo Please install Python 3.10+ and ensure it is added to your system PATH.
pause

:end
