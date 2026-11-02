#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/web_backend"
source venv/bin/activate
python -m pip install -r requirements-asgi.txt
python -m daphne -b 127.0.0.1 -p 8000 config.asgi:application
