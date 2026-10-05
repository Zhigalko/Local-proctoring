@echo off
chcp 65001 > nul
title Local proctoring - Kiosk Mode
echo ===================================================
echo   Запуск Local proctoring (Полноэкранный режим)
echo ===================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
pause
