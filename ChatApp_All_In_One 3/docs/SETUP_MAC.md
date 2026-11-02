# Mac setup

1. Extract the ZIP to Downloads.
2. Open Terminal and run `cd ~/Downloads/ChatApp_All_In_One` (adjust if extracted elsewhere).
3. Run `./setup_mac.command` or follow `START_HERE.txt` manually.
4. Run `./run_web.command` for HTTP/polling development.
5. For WebSockets, stop the first server and run `./run_asgi.command`.

If macOS blocks a script, run it from Terminal with `bash setup_mac.command`.
The setup script creates a virtual environment and database migrations; it does not
remove or overwrite a database file. Back up existing data before connecting MySQL.
