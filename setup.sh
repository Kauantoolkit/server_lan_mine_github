#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  Minecraft World Auto-Sync — Linux/macOS first-time setup
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "[setup] Installing Python dependencies..."
pip install -r requirements.txt

if [ ! -f config.json ]; then
    echo "[setup] Creating config.json from template..."
    cp config.example.json config.json
    echo "[setup] Open config.json and fill in:"
    echo "          world_path     — path to your Minecraft world folder"
    echo "          git.remote_url — your GitHub repo URL"
    echo "          rcon.password  — optional, for live-server commits"
    echo ""
    echo "[setup] Then run:  python sync.py --setup"
else
    echo "[setup] config.json already exists — skipping copy."
    echo "[setup] Run:  python sync.py --setup"
fi
