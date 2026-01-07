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

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

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
wait
