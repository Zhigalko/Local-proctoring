@echo off
title Local Proctoring System - Demo Day
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo   LOCAL PROCTORING SYSTEM (AI + KIOSK SECURITY)
echo   Запуск системы прокторинга для Demo Day...
echo ===================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" main.py
) else (
    python main.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ВНИМАНИЕ] Программа завершилась с кодом ошибки %ERRORLEVEL%.
)

pause
