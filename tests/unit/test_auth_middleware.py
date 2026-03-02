"""
Unit tests for API Key Auth Middleware
"""

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from provisioning_station.middleware.auth import ApiKeyAuthMiddleware, ws_auth_check
from provisioning_station.services.api_key_manager import ApiKeyManager


def _make_app(api_enabled: bool, manager: ApiKeyManager, monkeypatch=None) -> FastAPI:
    """Create a minimal FastAPI app with auth middleware and test routes.

    The middleware reads api_enabled from settings dynamically,
    so we patch settings.api_enabled to control it in tests.
    """
    if monkeypatch is not None:
        from provisioning_station.config import settings

        monkeypatch.setattr(settings, "api_enabled", api_enabled)

    app = FastAPI()
    app.add_middleware(
        ApiKeyAuthMiddleware,
        api_enabled=api_enabled,
        key_manager=manager,
    )

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/solutions")
    async def solutions():
        return {"solutions": []}

    @app.get("/api/restore/status")
    async def restore_status():
        return {"status": "idle"}

    @app.get("/api/serial-camera/test")
    async def serial_cam():
        return {"ok": True}

    @app.get("/api/keys")
    async def list_keys():
        return {"keys": []}

    @app.get("/docs")
    async def docs():
        return {"docs": True}

    @app.get("/")
    async def root():
        return {"root": True}

    @app.websocket("/ws/test")
    async def ws_test(websocket: WebSocket):
        if not await ws_auth_check(websocket, manager, api_enabled):
            return
        await websocket.accept()
        await websocket.send_json({"status": "connected"})
        await websocket.close()

    return app


@pytest.fixture
def manager(tmp_path):
    return ApiKeyManager(data_dir=tmp_path)


class TestAuthMiddleware:
    def test_localhost_no_auth_required(self, manager, monkeypatch):
        """127.0.0.1 requests pass without API key."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        # TestClient sends from 127.0.0.1 by default (testclient)
        resp = client.get("/api/solutions")
        assert resp.status_code == 200

    def test_health_always_public(self, manager, monkeypatch):
        """GET /api/health never requires auth."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app, headers={"x-forwarded-for": "192.168.1.100"})
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_docs_always_public(self, manager, monkeypatch):
        """/docs is always public."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_root_always_public(self, manager, monkeypatch):
        """/ is always public."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200

    def test_remote_without_key_returns_401(self, manager, monkeypatch):
        """Non-localhost request without key gets 401."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get("/api/solutions")
        assert resp.status_code == 401

    def test_remote_with_valid_key_passes(self, manager, monkeypatch):
        """Non-localhost with valid X-API-Key header gets 200."""
        key = manager.create_key("test")
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get("/api/solutions", headers={"X-API-Key": key})
        assert resp.status_code == 200

    def test_remote_with_bearer_token_passes(self, manager, monkeypatch):
        """Authorization: Bearer <key> format also works."""
        key = manager.create_key("bearer-test")
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get(
            "/api/solutions", headers={"Authorization": f"Bearer {key}"}
        )
        assert resp.status_code == 200

    def test_remote_with_invalid_key_returns_401(self, manager, monkeypatch):
        """Non-localhost with invalid key gets 401."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get("/api/solutions", headers={"X-API-Key": "ps_bogus"})
        assert resp.status_code == 401

    def test_api_disabled_remote_returns_403(self, manager, monkeypatch):
        """When api_enabled=false, non-localhost gets 403."""
        app = _make_app(api_enabled=False, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get("/api/solutions")
        assert resp.status_code == 403

    def test_internal_endpoint_blocked_for_remote(self, manager, monkeypatch):
        """Localhost-only endpoints return 403 for remote even with valid key."""
        key = manager.create_key("remote")
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        for path in ["/api/restore/status", "/api/serial-camera/test", "/api/keys"]:
            resp = client.get(path, headers={"X-API-Key": key})
            assert resp.status_code == 403, f"Expected 403 for {path}"

    def test_internal_endpoint_allowed_for_localhost(self, manager, monkeypatch):
        """Localhost-only endpoints pass for 127.0.0.1."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        resp = client.get("/api/restore/status")
        assert resp.status_code == 200
        resp = client.get("/api/keys")
        assert resp.status_code == 200


class TestQueryParamRestriction:
    """F6: ?api_key= query param is only accepted for /ws/ paths."""

    def test_query_param_rejected_for_api_path(self, manager, monkeypatch):
        """?api_key= on /api/solutions is NOT accepted — returns 401."""
        key = manager.create_key("qp-test")
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get(f"/api/solutions?api_key={key}")
        assert resp.status_code == 401

    def test_header_still_works_for_api_path(self, manager, monkeypatch):
        """X-API-Key header on /api/solutions is still accepted."""
        key = manager.create_key("header-test")
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)

        from provisioning_station.middleware import auth

        monkeypatch.setattr(auth, "_is_localhost", lambda r: False)

        client = TestClient(app)
        resp = client.get("/api/solutions", headers={"X-API-Key": key})
        assert resp.status_code == 200


class TestWsAuthCheck:
    """F1: WebSocket depth-of-defense auth."""

    def test_ws_localhost_passes(self, manager, monkeypatch):
        """Localhost WebSocket connections pass without key."""
        app = _make_app(api_enabled=True, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        # TestClient connects as "testclient" which is in _LOCALHOST_ADDRS
        with client.websocket_connect("/ws/test") as ws:
            data = ws.receive_json()
            assert data["status"] == "connected"

    def test_ws_localhost_passes_even_api_disabled(self, manager, monkeypatch):
        """Localhost WS passes even when api_enabled=False."""
        app = _make_app(api_enabled=False, manager=manager, monkeypatch=monkeypatch)
        client = TestClient(app)
        with client.websocket_connect("/ws/test") as ws:
            data = ws.receive_json()
            assert data["status"] == "connected"
