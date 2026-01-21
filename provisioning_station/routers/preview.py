"""
Preview Router - API endpoints for live preview functionality

Handles:
- RTSP stream proxy management (start/stop/status)
- HLS file serving
- MQTT to WebSocket bridge
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from ..services.stream_proxy import get_stream_proxy
from ..services.mqtt_bridge import get_mqtt_bridge, is_mqtt_available

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/preview", tags=["preview"])


# ============================================
# Request/Response Models
# ============================================

class StartStreamRequest(BaseModel):
    """Request to start an RTSP stream"""
    rtsp_url: str
    stream_id: Optional[str] = None


class StartStreamResponse(BaseModel):
    """Response from starting a stream"""
    stream_id: str
    hls_url: str
    status: str


class StreamStatusResponse(BaseModel):
    """Stream status response"""
    stream_id: str
    status: str
    error: Optional[str] = None


class MqttConnectRequest(BaseModel):
    """Request to connect to MQTT broker"""
    broker: str
    port: int = 1883
    topic: str
    username: Optional[str] = None
    password: Optional[str] = None


# ============================================
# Stream Proxy Endpoints
# ============================================

@router.post("/stream/start", response_model=StartStreamResponse)
async def start_stream(request: StartStreamRequest):
    """
    Start an RTSP to HLS stream proxy.

    This converts an RTSP stream to HLS format for browser playback.
    The HLS playlist will be available at /api/preview/stream/{stream_id}/index.m3u8
    """
    try:
        proxy = get_stream_proxy()
        stream_id = await proxy.start_stream(
            rtsp_url=request.rtsp_url,
            stream_id=request.stream_id,
        )

        return StartStreamResponse(
            stream_id=stream_id,
            hls_url=f"/api/preview/stream/{stream_id}/index.m3u8",
            status="starting",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start stream: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start stream: {str(e)}")


@router.post("/stream/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """Stop an RTSP stream proxy"""
    proxy = get_stream_proxy()
    if await proxy.stop_stream(stream_id):
        return {"status": "stopped", "stream_id": stream_id}
    else:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")


@router.get("/stream/{stream_id}/status", response_model=StreamStatusResponse)
async def get_stream_status(stream_id: str):
    """Get the status of a stream"""
    proxy = get_stream_proxy()
    info = proxy.get_stream_info(stream_id)

    if not info:
        raise HTTPException(status_code=404, detail=f"Stream {stream_id} not found")

    return StreamStatusResponse(
        stream_id=info.stream_id,
        status=info.status,
        error=info.error,
    )


@router.get("/stream/{stream_id}/{filename}")
async def get_stream_file(stream_id: str, filename: str):
    """
    Serve HLS stream files (playlist and segments).

    This endpoint serves the m3u8 playlist and .ts segment files.
    """
    proxy = get_stream_proxy()

    # Update last access time
    info = proxy.get_stream_info(stream_id)
    if info:
        import time
        info.last_accessed = time.time()

    file_path = proxy.get_stream_file(stream_id, filename)

    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Set appropriate content type
    if filename.endswith(".m3u8"):
        media_type = "application/vnd.apple.mpegurl"
    elif filename.endswith(".ts"):
        media_type = "video/mp2t"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache",
        }
    )


@router.get("/streams")
async def list_streams():
    """List all active streams"""
    proxy = get_stream_proxy()
    return {"streams": proxy.list_streams()}


# ============================================
# MQTT WebSocket Bridge
# ============================================

@router.websocket("/ws/mqtt")
async def mqtt_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for MQTT message forwarding.

    Client sends connection request:
    {
        "action": "connect",
        "broker": "192.168.1.100",
        "port": 1883,
        "topic": "inference/results",
        "username": "optional",
        "password": "optional"
    }

    Server sends messages:
    {
        "type": "mqtt_message",
        "topic": "inference/results",
        "payload": { ... parsed JSON ... },
        "timestamp": 1234567890.123
    }

    Or status updates:
    {
        "type": "status",
        "connected": true,
        "error": null
    }
    """
    await websocket.accept()

    if not is_mqtt_available():
        await websocket.send_json({
            "type": "error",
            "message": "MQTT functionality not available. Install paho-mqtt.",
        })
        await websocket.close()
        return

    bridge = get_mqtt_bridge()
    subscription_id = None
    message_queue: asyncio.Queue = asyncio.Queue()

    async def mqtt_callback(message):
        """Called when MQTT message is received"""
        await message_queue.put({
            "type": "mqtt_message",
            **message,
        })

    try:
        # Wait for connection request
        data = await websocket.receive_json()

        if data.get("action") != "connect":
            await websocket.send_json({
                "type": "error",
                "message": "Expected connect action",
            })
            return

        # Subscribe to MQTT topic
        try:
            subscription_id = await bridge.subscribe(
                broker=data["broker"],
                port=data.get("port", 1883),
                topic=data["topic"],
                callback=mqtt_callback,
                username=data.get("username"),
                password=data.get("password"),
            )

            await websocket.send_json({
                "type": "status",
                "connected": True,
                "subscription_id": subscription_id,
            })

        except Exception as e:
            await websocket.send_json({
                "type": "error",
                "message": f"Failed to connect to MQTT: {str(e)}",
            })
            return

        # Forward messages to WebSocket
        while True:
            try:
                # Check for MQTT messages with timeout
                message = await asyncio.wait_for(
                    message_queue.get(),
                    timeout=30.0  # Send ping every 30 seconds
                )
                await websocket.send_json(message)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})

                # Check subscription status
                info = bridge.get_subscription_info(subscription_id)
                if info and info.get("error"):
                    await websocket.send_json({
                        "type": "status",
                        "connected": False,
                        "error": info["error"],
                    })

    except WebSocketDisconnect:
        logger.info("MQTT WebSocket client disconnected")
    except Exception as e:
        logger.error(f"MQTT WebSocket error: {e}")
    finally:
        # Clean up subscription
        if subscription_id:
            await bridge.unsubscribe(subscription_id, mqtt_callback)


# ============================================
# Combined Preview WebSocket
# ============================================

@router.websocket("/ws/preview/{preview_id}")
async def preview_websocket(websocket: WebSocket, preview_id: str):
    """
    Combined WebSocket for preview functionality.

    Handles both stream status updates and MQTT message forwarding.

    Client sends:
    {
        "action": "start",
        "stream": {
            "rtsp_url": "rtsp://..."
        },
        "mqtt": {
            "broker": "...",
            "port": 1883,
            "topic": "..."
        }
    }

    Server sends various message types:
    - {"type": "stream_status", "status": "running", ...}
    - {"type": "mqtt_message", "payload": {...}, ...}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()

    proxy = get_stream_proxy()
    bridge = get_mqtt_bridge()

    stream_id = None
    subscription_id = None
    message_queue: asyncio.Queue = asyncio.Queue()

    async def mqtt_callback(message):
        await message_queue.put({
            "type": "mqtt_message",
            **message,
        })

    try:
        # Wait for start command
        data = await websocket.receive_json()

        if data.get("action") != "start":
            await websocket.send_json({
                "type": "error",
                "message": "Expected start action",
            })
            return

        # Start stream if configured
        stream_config = data.get("stream")
        if stream_config and stream_config.get("rtsp_url"):
            try:
                stream_id = await proxy.start_stream(
                    rtsp_url=stream_config["rtsp_url"],
                    stream_id=preview_id,
                )
                await websocket.send_json({
                    "type": "stream_status",
                    "status": "starting",
                    "stream_id": stream_id,
                    "hls_url": f"/api/preview/stream/{stream_id}/index.m3u8",
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "stream_error",
                    "message": str(e),
                })

        # Subscribe to MQTT if configured
        mqtt_config = data.get("mqtt")
        if mqtt_config and mqtt_config.get("broker") and mqtt_config.get("topic"):
            if is_mqtt_available():
                try:
                    subscription_id = await bridge.subscribe(
                        broker=mqtt_config["broker"],
                        port=mqtt_config.get("port", 1883),
                        topic=mqtt_config["topic"],
                        callback=mqtt_callback,
                        username=mqtt_config.get("username"),
                        password=mqtt_config.get("password"),
                    )
                    await websocket.send_json({
                        "type": "mqtt_status",
                        "connected": True,
                        "subscription_id": subscription_id,
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "mqtt_error",
                        "message": str(e),
                    })
            else:
                await websocket.send_json({
                    "type": "mqtt_error",
                    "message": "MQTT not available. Install paho-mqtt.",
                })

        # Check stream status periodically
        async def check_stream_status():
            while True:
                await asyncio.sleep(2)
                if stream_id:
                    info = proxy.get_stream_info(stream_id)
                    if info:
                        await message_queue.put({
                            "type": "stream_status",
                            "status": info.status,
                            "error": info.error,
                        })

        status_task = asyncio.create_task(check_stream_status())

        # Main message loop
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        message_queue.get(),
                        timeout=30.0
                    )
                    await websocket.send_json(message)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "ping"})
        finally:
            status_task.cancel()

    except WebSocketDisconnect:
        logger.info(f"Preview WebSocket {preview_id} disconnected")
    except Exception as e:
        logger.error(f"Preview WebSocket error: {e}")
    finally:
        # Clean up
        if stream_id:
            await proxy.stop_stream(stream_id)
        if subscription_id:
            await bridge.unsubscribe(subscription_id, mqtt_callback)


# ============================================
# Utility Endpoints
# ============================================

@router.get("/status")
async def get_preview_status():
    """Get overall preview service status"""
    return {
        "stream_proxy": {
            "available": True,
            "active_streams": len(get_stream_proxy().streams),
        },
        "mqtt_bridge": {
            "available": is_mqtt_available(),
            "active_subscriptions": len(get_mqtt_bridge().subscriptions) if is_mqtt_available() else 0,
        },
    }


@router.post("/cleanup")
async def cleanup_resources():
    """Clean up idle resources"""
    proxy = get_stream_proxy()
    await proxy.cleanup_idle_streams()
    return {"status": "cleanup completed"}
