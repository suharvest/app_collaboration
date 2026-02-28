#!/bin/bash
# ===========================================
# SenseCraft Solution Desktop Build Script
# Builds the Tauri desktop application locally
# ===========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
MODE="dev"
SKIP_SIDECAR=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            shift
            ;;
        --build)
            MODE="build"
            shift
            ;;
        --skip-sidecar)
            SKIP_SIDECAR=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev           Run in development mode (default)"
            echo "  --build         Build release package"
            echo "  --skip-sidecar  Skip sidecar build (use existing)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"

# ===========================================
# Step 1: Check prerequisites
# ===========================================
echo_info "Checking prerequisites..."

# Check Rust
if ! command -v cargo &> /dev/null; then
    echo_error "Rust/Cargo not found. Install from https://rustup.rs/"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo_error "Node.js not found. Install from https://nodejs.org/"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo_error "Python 3 not found."
    exit 1
fi

echo_info "All prerequisites met."

# ===========================================
# Step 2: Build sidecar (Python backend)
# ===========================================
if [ "$SKIP_SIDECAR" = false ]; then
    echo_info "Building Python sidecar..."

    # Build sidecar using uv (project uses uv for dependency management)
    uv run --group build python scripts/build-sidecar.py --clean

    echo_info "Sidecar build complete."
else
    echo_warn "Skipping sidecar build (--skip-sidecar flag)"

    # Check if sidecar exists
    if ! ls src-tauri/binaries/provisioning-station-* 1>/dev/null 2>&1; then
        echo_error "No sidecar binary found. Run without --skip-sidecar first."
        exit 1
    fi
fi

# ===========================================
# Step 3: Install frontend dependencies
# ===========================================
echo_info "Installing frontend dependencies..."
cd frontend
npm install
cd "$PROJECT_ROOT"

# ===========================================
# Step 4: Run Tauri
# ===========================================
if [ "$MODE" = "dev" ]; then
    echo_info "Starting Tauri development mode..."
    echo_info "This will open the app in a window with hot-reload enabled."
    echo ""

    cd src-tauri
    cargo tauri dev

elif [ "$MODE" = "build" ]; then
    echo_info "Building release package..."

    # Build frontend first
    cd frontend
    npm run build
    cd "$PROJECT_ROOT"

    # Build Tauri app
    cd src-tauri
    cargo tauri build

    echo ""
    echo_info "Build complete!"
    echo_info "Output location: src-tauri/target/release/bundle/"

    # Show the output files
    if [ -d "target/release/bundle" ]; then
        echo ""
        echo "Generated packages:"
        find target/release/bundle -type f \( -name "*.dmg" -o -name "*.app" -o -name "*.deb" -o -name "*.msi" -o -name "*.exe" \) 2>/dev/null | while read -r file; do
            size=$(du -h "$file" | cut -f1)
            echo "  - $file ($size)"
        done
    fi
fi
