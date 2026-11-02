#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/web_backend"
source venv/bin/activate
python manage.py runserver
