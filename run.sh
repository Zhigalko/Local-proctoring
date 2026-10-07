#!/usr/bin/env bash
# One-click launcher for Local Proctoring System on Linux/macOS

cd "$(dirname "$0")"

echo "==================================================="
echo "  LOCAL PROCTORING SYSTEM (AI + KIOSK SECURITY)"
echo "  Запуск системы прокторинга..."
echo "==================================================="

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python main.py "$@"
elif [ -f "venv/bin/python" ]; then
    venv/bin/python main.py "$@"
else
    python3 main.py "$@"
fi
