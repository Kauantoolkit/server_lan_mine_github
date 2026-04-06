# Minecraft World Auto-Sync

Automatically detects changes in a Minecraft server world and commits + pushes them to GitHub. Another player can `git pull` to grab the latest world and continue playing.

## How it works

```
Minecraft server writes chunks
         ↓
watchdog detects changed .mca / .dat files
         ↓
debounce timer resets on each new event (default 30s)
         ↓
no activity for 30s → commit window opens
         ↓
(if RCON configured) save-all flush → save-off
         ↓
git add --all → git commit → git push
         ↓
(if RCON) save-on
```

### Save corruption prevention

| Situation | Behavior |
|---|---|
| RCON configured + server running | `save-all flush`, then `save-off` before commit, `save-on` after |
| No RCON + server stopped (session.lock > 60s old) | Commits safely |
| No RCON + server appears running | **Skips** commit, logs a warning |

---

## Requirements

- Python 3.8+
- git
- A GitHub repository (empty or existing)

---

## Setup

### 1. Clone / download this folder

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO
```

Or just copy the files to a folder next to your Minecraft server.

### 2. Install dependencies

**Windows:**
```
setup.bat
```

**Linux / macOS:**
```bash
bash setup.sh
```

### 3. Configure

Edit `config.json` (created by setup):

```json
{
  "world_path": "C:/MinecraftServer/world",
  "repo_path": ".",
  "debounce_seconds": 30,
  "offline_grace_seconds": 60,
  "rcon": {
    "host": "127.0.0.1",
    "port": 25575,
    "password": "your_rcon_password"
  },
  "git": {
    "remote_url": "https://github.com/YOUR_USER/YOUR_REPO.git",
    "remote": "origin",
    "branch": "main"
  },
  "logging": {
    "level": "INFO",
    "file": "sync.log"
  }
}
```

> `config.json` is gitignored — your RCON password stays local.

#### Enable RCON on your Minecraft server

In `server.properties`:
```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_rcon_password
broadcast-rcon-to-ops=false
```

### 4. First push

```bash
python sync.py --setup
```

This initializes the git repo, sets the remote, and pushes a first snapshot.

### 5. Start watching

```bash
python sync.py
```

Leave this running alongside your Minecraft server. Every time the world changes and is quiet for 30 seconds, it commits and pushes.

---

## Pulling the world on another machine

```bash
# First time — clone the repo
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO

# Copy the world folder to your Minecraft server directory, then start the server

# Later sessions — pull latest before starting server
python sync.py --pull
# or just:
git pull
```

> Always pull **before** starting the server. Starting the server while the world is behind will cause the watcher on the original machine to conflict.

---

## Running as a background service

### Windows (Task Scheduler)
1. Open Task Scheduler → Create Basic Task
2. Trigger: At log on (or at startup)
3. Action: `python C:\path\to\sync.py --config C:\path\to\config.json`

### Windows (run minimized)
```batch
start /min python sync.py
```

### Linux (systemd)
```ini
[Unit]
Description=Minecraft World Sync
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/mc-sync/sync.py --config /opt/mc-sync/config.json
Restart=on-failure
User=minecraft

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now mc-sync
```

---

## What is tracked vs ignored

**Tracked** (important world data):
- `world/` — Overworld region files, player data, level.dat
- `world_nether/` — Nether
- `world_the_end/` — End
- `server.properties`
- `ops.json`, `whitelist.json`, `banned-*.json`

**Ignored** (via `.gitignore`):
- `*.jar` — Server binaries (too large, not world data)
- `logs/`, `crash-reports/` — Runtime noise
- `**/session.lock` — Changes every second while server runs
- `usercache.json` — Regenerated automatically
- `plugins/`, `mods/` — Keep in a separate repo
- `config.json` — Contains RCON password

---

## Large worlds and Git LFS

Minecraft region files (`.mca`) are binary and can be large. For worlds > ~1 GB, consider [Git LFS](https://git-lfs.github.com/):

```bash
git lfs install
git lfs track "*.mca"
git lfs track "*.dat"
git add .gitattributes
```

---

## Workflow summary

```
Player A finishes session → server saves → sync.py commits + pushes
Player B wants to play   → git pull (or python sync.py --pull) → start server
Player B finishes        → same auto-sync happens
Player A resumes         → git pull → start server
```
