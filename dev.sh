#!/bin/bash

# Provisioning Station - Development Mode with Hot Reload
# Runs backend and frontend in development mode

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=3260
FRONTEND_PORT=5173

echo "=========================================="
echo "  Provisioning Station - Dev Mode"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Track child PIDs
BACKEND_PID=""
FRONTEND_PID=""
CLEANUP_DONE=0

# Function to kill process and all its children
kill_tree() {
    local pid=$1
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        # Kill all child processes first
        pkill -P "$pid" 2>/dev/null || true
        # Then kill the parent
        kill "$pid" 2>/dev/null || true
        # Wait for process to terminate
        wait "$pid" 2>/dev/null || true
    fi
}

# Function to cleanup on exit
cleanup() {
    # Prevent duplicate cleanup
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi
    CLEANUP_DONE=1

    echo ""
    echo "Shutting down..."

    # Kill process trees
    kill_tree "$BACKEND_PID"
    kill_tree "$FRONTEND_PID"

    # Extra cleanup: kill any remaining processes on our ports
    lsof -ti:$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    lsof -ti:$FRONTEND_PORT | xargs kill -9 2>/dev/null || true

    echo "All processes terminated."
}

# Trap all exit signals
trap cleanup SIGINT SIGTERM EXIT

# Check dependencies
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed"
    exit 1
fi

# Install dependencies
echo -e "${BLUE}[1/3]${NC} Syncing dependencies..."
cd "$PROJECT_DIR"
uv sync --quiet

cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    npm install --silent
fi

# Start servers
echo -e "${BLUE}[2/3]${NC} Starting backend (port $BACKEND_PORT)..."
cd "$PROJECT_DIR"
uv run uvicorn provisioning_station.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!

sleep 1

echo -e "${BLUE}[3/3]${NC} Starting frontend dev server (port $FRONTEND_PORT)..."
cd "$PROJECT_DIR/frontend"
npm run dev -- --port $FRONTEND_PORT &
FRONTEND_PID=$!

sleep 2

echo ""
echo "=========================================="
echo -e "${GREEN}Development servers running!${NC}"
echo ""
echo -e "  ${YELLOW}Frontend:${NC} http://localhost:${FRONTEND_PORT}"
echo -e "  ${YELLOW}Backend:${NC}  http://localhost:${BACKEND_PORT}"
echo -e "  ${YELLOW}API:${NC}      http://localhost:${BACKEND_PORT}/api"
echo ""
echo "  Press Ctrl+C to stop all servers"
echo "=========================================="

# Wait for either process to exit
# Using a loop so that signals can interrupt wait
while true; do
    # Check if processes are still running
    if ! kill -0 "$BACKEND_PID" 2>/dev/null && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "All processes have exited."
        break
    fi
    sleep 1
done
