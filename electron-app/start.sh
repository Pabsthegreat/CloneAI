#!/bin/bash

# CloneAI Desktop Launcher
# Starts both Python backend and Electron frontend

echo "🤖 Starting CloneAI Desktop..."

# Get script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Python virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${RED}❌ Python virtual environment not found!${NC}"
    echo "Please set up CloneAI first:"
    echo "  cd $PROJECT_ROOT"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "$DIR/node_modules" ]; then
    echo -e "${YELLOW}⚠️  node_modules not found. Installing dependencies...${NC}"
    cd "$DIR"
    npm install
fi

# Start Python backend in background
echo -e "${GREEN}▶️  Starting Python backend...${NC}"
source "$PROJECT_ROOT/.venv/bin/activate"
cd "$PROJECT_ROOT"
python -m agent.server.api > /tmp/cloneai-backend.log 2>&1 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"

# Wait a bit for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Backend failed to start!${NC}"
    echo "Check logs: /tmp/cloneai-backend.log"
    exit 1
fi

# Start Electron
echo -e "${GREEN}▶️  Starting Electron app...${NC}"
cd "$DIR"
npm start

# Cleanup: Kill backend when Electron closes
echo -e "${YELLOW}🛑 Stopping backend...${NC}"
kill $BACKEND_PID 2>/dev/null

echo -e "${GREEN}✅ CloneAI Desktop closed${NC}"
