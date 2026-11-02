#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/web_backend"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ ! -d venv ]; then "$PYTHON_BIN" -m venv venv; fi
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py makemigrations chat
python manage.py migrate
python manage.py check
echo "\nBase setup completed. Start the web app with: cd web_backend && source venv/bin/activate && python manage.py runserver"
