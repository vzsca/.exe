#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "================================"
echo "       .exe Launcher"
echo "================================"
if command -v python3 >/dev/null 2>&1; then PYTHON=python3
elif command -v python >/dev/null 2>&1; then PYTHON=python
else echo "[ERROR] Python 3 was not found."; exit 1
fi
if [ ! -d venv ]; then "$PYTHON" -m venv venv; fi
venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -e . -r requirements-dev.txt
if [ ! -f .env ]; then cp .env.example .env; chmod 600 .env; fi
exec venv/bin/python panel.py
