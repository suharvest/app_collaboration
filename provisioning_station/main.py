"""
FastAPI application entry point
"""

import asyncio
import atexit
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

# Windows requires ProactorEventLoop for asyncio subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configure application logging (uvicorn only sets up its own loggers)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t %(name)s - %(message)s")
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import (
    deployments,
    device_management,
    devices,
    docker_devices,
    preview,
    restore,
    solutions,
    versions,
    websocket,
)
from .services.mqtt_bridge import get_mqtt_bridge, is_mqtt_available
from .services.solution_manager import solution_manager
from .services.stream_proxy import get_stream_proxy

# Global flag to track if cleanup has been performed
_cleanup_done = False
_event_loop: Optional[asyncio.AbstractEventLoop] = None


def _sync_cleanup():
    """Synchronous cleanup for atexit handler (last resort)"""
    global _cleanup_done
    if _cleanup_done:
        return

    logger.debug("Running synchronous cleanup (atexit)...")

    # Try to stop FFmpeg processes synchronously
    try:
        stream_proxy = get_stream_proxy()
        # Kill any running FFmpeg processes directly
        for stream_id, stream_info in list(stream_proxy._streams.items()):
            if stream_info.process and stream_info.process.returncode is None:
                try:
                    stream_info.process.kill()
                except Exception:
                    pass
    except Exception as e:
        logger.debug(f"Sync cleanup error: {e}")

    _cleanup_done = True


async def _async_cleanup():
    """Async cleanup for graceful shutdown"""
    global _cleanup_done
    if _cleanup_done:
        return

    logger.debug("Running async cleanup...")

    try:
        await get_stream_proxy().stop_all()
        logger.debug("Stream proxy stopped")
    except Exception as e:
        logger.debug(f"Stream proxy cleanup error: {e}")

    try:
        if is_mqtt_available():
            await get_mqtt_bridge().stop_all()
            logger.debug("MQTT bridge stopped")
    except Exception as e:
        logger.debug(f"MQTT bridge cleanup error: {e}")

    _cleanup_done = True
    logger.debug("Async cleanup completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global _event_loop

    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Solutions directory: {settings.solutions_dir}")
    print(f"Platform: {sys.platform}")

    # Store event loop for signal handlers
    _event_loop = asyncio.get_running_loop()

    # Register atexit handler as last resort cleanup
    atexit.register(_sync_cleanup)

    # Ensure directories exist
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    # Load solutions
    await solution_manager.load_solutions()
    print(f"Loaded {len(solution_manager.solutions)} solutions")

    yield

    # Shutdown - this runs when uvicorn receives SIGTERM/SIGINT
    logger.debug("Shutting down (lifespan)...")

    # Cleanup preview services
    await _async_cleanup()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="IoT Solution Provisioning Platform for Seeed Studio products",
    lifespan=lifespan,
)

# CORS middleware (for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(solutions.router)
app.include_router(devices.router)
app.include_router(deployments.router)
app.include_router(websocket.router)
app.include_router(versions.router)
app.include_router(device_management.router)
app.include_router(preview.router)
app.include_router(docker_devices.router)
app.include_router(restore.router)

# Serve static frontend files
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_dist / "index.html")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


def main():
    """CLI entry point"""
    import argparse
    import os
    import sys

    import uvicorn

    # Check if running as frozen executable
    is_frozen = getattr(sys, 'frozen', False)
    print(f"Starting provisioning-station (frozen={is_frozen})")

    parser = argparse.ArgumentParser(
        description="SenseCraft Solution Provisioning Station"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help=f"Port to listen on (default: {settings.port})"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=settings.host,
        help=f"Host to bind to (default: {settings.host})"
    )
    parser.add_argument(
        "--solutions-dir",
        type=str,
        default=None,
        help="Path to solutions directory (overrides default)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reload (for development)"
    )
    args = parser.parse_args()

    # Set solutions dir via environment variable if provided
    # This will be picked up when uvicorn imports the app
    if args.solutions_dir:
        os.environ["PS_SOLUTIONS_DIR"] = args.solutions_dir

    if is_frozen:
        # For frozen executables, pass the app object directly to avoid
        # module reimport issues where sys.frozen might not be preserved
        # Also disable reload since it doesn't work with frozen apps
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=False,
        )
    else:
        # For development, use string reference to enable hot reload
        uvicorn.run(
            "provisioning_station.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main()
