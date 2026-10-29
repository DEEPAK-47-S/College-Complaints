@echo off
title AUGIS - AICTE Unified Grievance Intelligence System
color 0B

echo ===============================================================================
echo                AICTE UNIFIED GRIEVANCE INTELLIGENCE SYSTEM (AUGIS)
echo      Integrated Institution Complaint Monitoring ^& Intelligent Cross-Bureau
echo                        Coordination Platform (AICTE PS-2)
echo ===============================================================================
echo.

:: 1. Detect Python Environment
set PYTHON_EXE=.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [!] Local virtual environment (.venv) not found. Checking system python...
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_EXE=python
    ) else (
        echo [ERROR] Python was not found on your system! Please install Python 3.12+.
        pause
        exit /b 1
    )
)

echo [*] Using Python: %PYTHON_EXE%
echo [*] Initializing database migrations...
"%PYTHON_EXE%" manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Migration check failed. Please inspect database configuration.
    pause
    exit /b 1
)

echo.
echo [*] System check passed successfully.
echo [*] Default Login Credentials:
echo     - Super Administrator  : admin          / Augis@2026
echo     - Bureau Head (RB)     : rb_head        / Augis@2026
echo     - Bureau Head (PGRC)   : pgrc_head      / Augis@2026
echo     - Regional Officer     : ro_north       / Augis@2026
echo     - Senior Management    : senior_mgmt    / Augis@2026
echo     - Competent Authority  : competent_auth / Augis@2026
echo.
echo [*] Launching AUGIS Portal at: http://127.0.0.1:8000/accounts/login/
echo.

:: Open browser in background after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/accounts/login/"

:: Start Django Development Server
"%PYTHON_EXE%" manage.py runserver 127.0.0.1:8000

pause
