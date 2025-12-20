#!/bin/zsh

# CloneAI Auto-Start on Wake
# This script starts both the Python backend and Electron UI

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="/tmp/cloneai-autostart.log"

echo "[$(date)] Starting CloneAI on system wake..." >> "$LOG_FILE"

# Check if backend is already running
if pgrep -f "agent.server.api" > /dev/null; then
    echo "[$(date)] Backend already running, skipping..." >> "$LOG_FILE"
else
    echo "[$(date)] Starting Python backend..." >> "$LOG_FILE"
    # Navigate to project root (one level up from shell-scripts)
    cd "$SCRIPT_DIR/.."
    
    # Start backend in background
    source .venv/bin/activate
    nohup python -m agent.server.api >> /tmp/cloneai-backend.log 2>&1 &
    
    echo "[$(date)] Backend started (PID: $!)" >> "$LOG_FILE"
    
    # Wait for backend to be ready
    sleep 3
fi

# Check if Electron app is already running
if pgrep -f "electron.*cloneai" > /dev/null; then
    echo "[$(date)] Electron app already running, skipping..." >> "$LOG_FILE"
else
    echo "[$(date)] Starting Electron UI..." >> "$LOG_FILE"
    # Navigate to electron-app (sibling of shell-scripts)
    cd "$SCRIPT_DIR/../electron-app"
    
    # Start Electron app (it will run in foreground but detached)
    nohup npm start >> /tmp/cloneai-ui.log 2>&1 &
    
    echo "[$(date)] Electron UI started (PID: $!)" >> "$LOG_FILE"
fi

echo "[$(date)] CloneAI startup complete!" >> "$LOG_FILE"
