"""
FastAPI application entry point
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Configure application logging (uvicorn only sets up its own loggers)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:\t %(name)s - %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import settings
from .routers import solutions, devices, deployments, websocket, versions, device_management, preview, docker_devices, restore
from .services.solution_manager import solution_manager
from .services.stream_proxy import get_stream_proxy
from .services.mqtt_bridge import get_mqtt_bridge, is_mqtt_available


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Solutions directory: {settings.solutions_dir}")

    # Ensure directories exist
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)

    # Load solutions
    await solution_manager.load_solutions()
    print(f"Loaded {len(solution_manager.solutions)} solutions")

    yield

    # Shutdown
    print("Shutting down...")

    # Cleanup preview services
    try:
        await get_stream_proxy().stop_all()
        if is_mqtt_available():
            await get_mqtt_bridge().stop_all()
    except Exception as e:
        print(f"Preview cleanup error: {e}")


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
    import uvicorn

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
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reload (for development)"
    )
    args = parser.parse_args()

    uvicorn.run(
        "provisioning_station.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
