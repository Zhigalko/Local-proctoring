@echo off
chcp 65001 > nul
title Local proctoring - Windowed Mode
echo ===================================================
echo   Запуск Local proctoring (Оконный режим)
echo ===================================================
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py --windowed
) else (
    python run.py --windowed
)
pause
