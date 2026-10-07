@echo off
title Proctor Admin Dashboard - Demo Day
chcp 65001 >nul
cd /d "%~dp0"

echo ===================================================
echo   PROCTOR ADMIN DASHBOARD (Панель преподавателя)
echo   Запуск панели проверки сессий и нарушений...
echo ===================================================

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" admin.py
) else if exist "venv\Scripts\python.exe" (
    "venv\Scripts\python.exe" admin.py
) else (
    python admin.py
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ВНИМАНИЕ] Программа завершилась с кодом ошибки %ERRORLEVEL%.
)

pause
