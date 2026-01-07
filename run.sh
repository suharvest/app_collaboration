#!/bin/bash

# Provisioning Station - Development Run Script
# This script starts both backend and frontend servers

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=3260
FRONTEND_PORT=5173

echo "=========================================="
echo "  Provisioning Station - Development Mode"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js first."
    exit 1
fi

# Install backend dependencies if needed
echo -e "${BLUE}[1/4]${NC} Checking backend dependencies..."
cd "$PROJECT_DIR"
uv sync --quiet

# Install frontend dependencies if needed
echo -e "${BLUE}[2/4]${NC} Checking frontend dependencies..."
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    npm install --silent
fi

# Build frontend for production serving
echo -e "${BLUE}[3/4]${NC} Building frontend..."
npm run build --silent 2>/dev/null || npm run build

# Start backend server
echo -e "${BLUE}[4/4]${NC} Starting servers..."
echo ""
cd "$PROJECT_DIR"

# Start backend (serves both API and static files)
echo -e "${GREEN}Starting backend on http://localhost:${BACKEND_PORT}${NC}"
uv run uvicorn provisioning_station.main:app --host 0.0.0.0 --port $BACKEND_PORT &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

echo ""
echo "=========================================="
echo -e "${GREEN}Provisioning Station is running!${NC}"
echo ""
echo "  Open: http://localhost:${BACKEND_PORT}"
echo ""
echo "  Press Ctrl+C to stop"
echo "=========================================="

# Wait for backend process
wait $BACKEND_PID
