@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  Minecraft World Auto-Sync — Windows first-time setup
REM ─────────────────────────────────────────────────────────────────────────────

echo [setup] Installing Python dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Make sure Python 3.8+ is installed and in PATH.
    pause
    exit /b 1
)

if not exist config.json (
    echo [setup] Creating config.json from template...
    copy config.example.json config.json
    echo [setup] Open config.json and fill in:
    echo         - world_path   (path to your Minecraft world folder)
    echo         - git.remote_url (your GitHub repo URL)
    echo         - rcon.password  (optional, for live-server commits)
    echo.
    echo [setup] Then run:  python sync.py --setup
) else (
    echo [setup] config.json already exists — skipping copy.
    echo [setup] Run:  python sync.py --setup
)

pause
