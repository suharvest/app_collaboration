"""
API Key authentication middleware.

Rules (by priority):
1. Public paths (/api/health, /docs, /openapi.json, /redoc, /assets/*, /) → pass
2. Localhost (127.0.0.1, ::1) → always pass
3. api_enabled=false → non-localhost gets 403
4. Localhost-only prefixes → non-localhost gets 403
5. WebSocket (/ws/) → validate ?api_key= query param
6. Other → validate X-API-Key header or Authorization: Bearer
"""

import logging
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Paths that never require authentication
PUBLIC_PATHS = frozenset({"/api/health", "/docs", "/openapi.json", "/redoc", "/"})

# Path prefixes that are always public
PUBLIC_PREFIXES = ("/assets/",)

# Localhost-only path prefixes (blocked for remote even with valid key)
LOCALHOST_ONLY_PREFIXES = (
    "/api/restore",
    "/api/serial-camera",
    "/api/docker-devices/local",
    "/api/device-management",
    "/api/preview",
    "/api/keys",
)

_LOCALHOST_ADDRS = frozenset({"127.0.0.1", "::1", "testclient"})


def _is_localhost(conn) -> bool:
    """Check if a connection is from localhost. Works for both Request and WebSocket."""
    client = conn.client
    if client is None:
        return False
    return client.host in _LOCALHOST_ADDRS


def _extract_api_key(request: Request) -> str | None:
    """Extract API key from header or query param.

    Query param (?api_key=) is only accepted for /ws/ paths (WebSocket).
    """
    # X-API-Key header
    key = request.headers.get("x-api-key")
    if key:
        return key

    # Authorization: Bearer <key>
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    # Query param — only allowed for /ws/ paths
    if request.url.path.startswith("/ws/"):
        key = request.query_params.get("api_key")
        if key:
            return key

    return None


async def ws_auth_check(websocket: "WebSocket", key_manager, api_enabled: bool) -> bool:
    """Pre-accept auth check for WebSocket handlers.

    Returns True if the connection is allowed. On failure, sends a close
    frame with an application-level close code (RFC 6455 §7.4.2: 4000-4999)
    and returns False.

    Close codes:
      4401 — missing or invalid API key
      4403 — API access not enabled for non-localhost
    """
    # Localhost always passes
    if _is_localhost(websocket):
        return True

    # API not enabled — reject non-localhost
    if not api_enabled:
        await websocket.close(code=4403, reason="API access is not enabled")
        return False

    # Extract key from query param
    api_key = websocket.query_params.get("api_key")

    if not api_key or key_manager is None:
        await websocket.close(code=4401, reason="API key required")
        return False

    record = key_manager.validate_key(api_key)
    if record is None:
        await websocket.close(code=4401, reason="Invalid API key")
        return False

    return True


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces API key auth for non-localhost requests.

    api_enabled is read from settings at dispatch time so that runtime
    changes (e.g. --api-enabled in frozen mode) take effect immediately.
    """

    def __init__(self, app, api_enabled: bool = False, key_manager=None):
        super().__init__(app)
        self._api_enabled_init = api_enabled
        self.key_manager = key_manager

    @property
    def api_enabled(self) -> bool:
        """Read api_enabled dynamically from settings (falls back to init value)."""
        try:
            from ..config import settings

            return settings.api_enabled
        except Exception:
            return self._api_enabled_init

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 1. Public paths
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        # 2. Localhost — always pass
        if _is_localhost(request):
            return await call_next(request)

        # 3. API not enabled — block all non-localhost
        if not self.api_enabled:
            return JSONResponse(
                status_code=403,
                content={"detail": "API access is not enabled"},
            )

        # 4. Localhost-only endpoints
        if any(path.startswith(p) for p in LOCALHOST_ONLY_PREFIXES):
            return JSONResponse(
                status_code=403,
                content={"detail": "This endpoint is only available from localhost"},
            )

        # 5 & 6. Validate API key
        api_key = _extract_api_key(request)
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "API key required. Use X-API-Key header or Authorization: Bearer <key>"
                },
            )

        if self.key_manager is None:
            return JSONResponse(
                status_code=500,
                content={"detail": "Key manager not configured"},
            )

        record = self.key_manager.validate_key(api_key)
        if record is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key"},
            )

        return await call_next(request)
