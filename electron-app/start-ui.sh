#!/bin/bash

# Simple Electron launcher (assumes backend is already running)

echo "🤖 Starting CloneAI Desktop (Electron only)..."
echo "Note: Make sure Python backend is running on port 8765"
echo ""

# Check if backend is running
if ! curl -s http://127.0.0.1:8765/api/health > /dev/null 2>&1; then
    echo "⚠️  Backend not detected on port 8765"
    echo "Start it with: python -m agent.server.api"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Electron
cd "$(dirname "$0")"
ELECTRON_DISABLE_SECURITY_WARNINGS=true npm start
