"""
WebSocket routes for real-time log streaming
"""

import asyncio
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.deployment_engine import deployment_engine

router = APIRouter()


class ConnectionManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, deployment_id: str):
        """Accept and register a WebSocket connection"""
        await websocket.accept()
        if deployment_id not in self.active_connections:
            self.active_connections[deployment_id] = set()
        self.active_connections[deployment_id].add(websocket)

    def disconnect(self, websocket: WebSocket, deployment_id: str):
        """Remove a WebSocket connection"""
        if deployment_id in self.active_connections:
            self.active_connections[deployment_id].discard(websocket)
            if not self.active_connections[deployment_id]:
                del self.active_connections[deployment_id]

    async def broadcast(self, deployment_id: str, message: dict):
        """Broadcast message to all connections for a deployment"""
        if deployment_id in self.active_connections:
            dead_connections = set()
            for websocket in self.active_connections[deployment_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    dead_connections.add(websocket)

            # Clean up dead connections
            for ws in dead_connections:
                self.active_connections[deployment_id].discard(ws)

    def has_connections(self, deployment_id: str) -> bool:
        """Check if deployment has active connections"""
        return (
            deployment_id in self.active_connections
            and len(self.active_connections[deployment_id]) > 0
        )


manager = ConnectionManager()

# Register manager with deployment engine
deployment_engine.set_websocket_manager(manager)


@router.websocket("/ws/logs/{deployment_id}")
async def websocket_logs(websocket: WebSocket, deployment_id: str):
    """WebSocket endpoint for real-time deployment logs"""
    await manager.connect(websocket, deployment_id)

    try:
        # Send initial status
        deployment = deployment_engine.get_deployment(deployment_id)
        if deployment:
            await websocket.send_json(
                {
                    "type": "status",
                    "deployment_id": deployment_id,
                    "status": deployment.status.value,
                }
            )

            # Send existing logs
            for log in deployment.logs[-50:]:  # Last 50 logs
                await websocket.send_json(
                    {
                        "type": "log",
                        "timestamp": log.timestamp.isoformat(),
                        "level": log.level,
                        "device_id": log.device_id,
                        "step_id": log.step_id,
                        "message": log.message,
                    }
                )

        # Keep connection alive and handle client messages
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=30.0  # Ping every 30 seconds
                )
                # Handle client messages if needed
                if data == "ping":
                    await websocket.send_json({"type": "pong"})

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, deployment_id)


@router.websocket("/ws/all")
async def websocket_all_logs(websocket: WebSocket):
    """WebSocket endpoint for all deployment logs (admin view)"""
    await websocket.accept()

    # Track which deployments we're subscribed to
    subscribed: Set[str] = set()

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("action") == "subscribe":
                deployment_id = data.get("deployment_id")
                if deployment_id:
                    await manager.connect(websocket, deployment_id)
                    subscribed.add(deployment_id)
                    await websocket.send_json(
                        {
                            "type": "subscribed",
                            "deployment_id": deployment_id,
                        }
                    )

            elif data.get("action") == "unsubscribe":
                deployment_id = data.get("deployment_id")
                if deployment_id and deployment_id in subscribed:
                    manager.disconnect(websocket, deployment_id)
                    subscribed.discard(deployment_id)
                    await websocket.send_json(
                        {
                            "type": "unsubscribed",
                            "deployment_id": deployment_id,
                        }
                    )

    except WebSocketDisconnect:
        pass
    finally:
        # Clean up all subscriptions
        for deployment_id in subscribed:
            manager.disconnect(websocket, deployment_id)
