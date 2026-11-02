CHATAPP UPGRADE — START HERE

This is a starter upgrade package built around your uploaded pastel pink/lavender chat.html and style.css. It includes Django/MySQL settings, your existing Conversation/Message model structure, basic message endpoints, sidebar unread-count endpoint, and a Channels WebSocket endpoint for typing events.

IMPORTANT:
- This is NOT yet a complete production WhatsApp clone.
- The WebSocket endpoint currently supports typing/stop_typing events. Message sending still uses your existing HTTP endpoint; the next integration step is to switch message delivery to WebSocket events.
- The Channels layer is in-memory for local testing only. Use Redis for multiple workers/production.
- A registration page, profile/media features, groups, encryption, calls, and full mobile navigation are not implemented yet.
- Your uploaded SQLite database is NOT overwritten or automatically converted. Keep a backup. The settings in this starter target a separate MySQL database.

SETUP ON MAC:
1. Unzip this folder.
2. Open Terminal and cd into the ChatApp_Upgrade folder.
3. Create and activate a virtual environment:
   python3 -m venv venv
   source venv/bin/activate
4. Install dependencies:
   pip install -r requirements.txt
5. Copy .env.example to .env and enter your MySQL database name, username and password.
6. Create the empty MySQL database (example):
   CREATE DATABASE chatapp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
7. Run:
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver

Before using this as a replacement for your existing project, we need to compare your actual config/settings.py, chat/models.py, chat/views.py and URL files. Do not delete your original ChatApp or db.sqlite3.
