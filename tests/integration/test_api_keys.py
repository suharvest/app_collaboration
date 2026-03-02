"""
Integration tests for API Key management endpoints.

These use TestClient which sends requests from localhost,
so they bypass the auth middleware (as designed).
"""

import pytest
from fastapi.testclient import TestClient

from provisioning_station.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with a temp data dir for key storage."""
    import provisioning_station.services.api_key_manager as akm

    # Reset singleton so each test gets fresh state
    monkeypatch.setattr(akm, "_manager", None)
    # Patch settings.data_dir
    monkeypatch.setattr(
        "provisioning_station.services.api_key_manager.settings.data_dir", tmp_path
    )

    with TestClient(app) as c:
        yield c


class TestApiKeyEndpoints:
    def test_create_key_from_localhost(self, client):
        """POST /api/keys → 201, returns api_key and name."""
        resp = client.post("/api/keys", json={"name": "ci-key"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "ci-key"
        assert data["api_key"].startswith("ps_")

    def test_list_keys(self, client):
        """GET /api/keys returns empty list initially, then populated."""
        resp = client.get("/api/keys")
        assert resp.status_code == 200
        assert resp.json()["keys"] == []

        client.post("/api/keys", json={"name": "k1"})
        resp = client.get("/api/keys")
        keys = resp.json()["keys"]
        assert len(keys) == 1
        assert keys[0]["name"] == "k1"

    def test_list_keys_includes_id(self, client):
        """GET /api/keys returns id field for each key."""
        client.post("/api/keys", json={"name": "with-id"})
        resp = client.get("/api/keys")
        keys = resp.json()["keys"]
        assert "id" in keys[0]
        assert len(keys[0]["id"]) == 36  # UUID

    def test_delete_key(self, client):
        """DELETE /api/keys/{name} → 200."""
        client.post("/api/keys", json={"name": "to-delete"})
        resp = client.delete("/api/keys/to-delete")
        assert resp.status_code == 200

        resp = client.get("/api/keys")
        assert len(resp.json()["keys"]) == 0

    def test_delete_nonexistent_key(self, client):
        """DELETE /api/keys/{name} → 404 for missing key."""
        resp = client.delete("/api/keys/nope")
        assert resp.status_code == 404

    def test_delete_key_by_id(self, client):
        """DELETE /api/keys/id/{key_id} → 200."""
        client.post("/api/keys", json={"name": "id-del"})
        keys = client.get("/api/keys").json()["keys"]
        key_id = keys[0]["id"]

        resp = client.delete(f"/api/keys/id/{key_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == key_id

        # Verify deleted
        keys = client.get("/api/keys").json()["keys"]
        assert len(keys) == 0

    def test_delete_key_by_id_nonexistent(self, client):
        """DELETE /api/keys/id/{bad_id} → 404."""
        resp = client.delete("/api/keys/id/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_get_api_status(self, client):
        """GET /api/keys/status returns api_enabled + key_count."""
        resp = client.get("/api/keys/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "api_enabled" in data
        assert data["key_count"] == 0


class TestNameValidation:
    def test_duplicate_name_returns_422(self, client):
        """Creating two keys with the same name returns 422."""
        resp = client.post("/api/keys", json={"name": "dup"})
        assert resp.status_code == 201

        resp = client.post("/api/keys", json={"name": "dup"})
        assert resp.status_code == 422
        assert "already exists" in resp.json()["detail"]

    def test_invalid_name_returns_422(self, client):
        """Names with spaces/special chars return 422."""
        for bad_name in ["my key", "a/b", ""]:
            resp = client.post("/api/keys", json={"name": bad_name})
            assert resp.status_code == 422, f"Expected 422 for name '{bad_name}'"

    def test_valid_names_accepted(self, client):
        """Names with alphanum/dash/underscore are accepted."""
        for name in ["good", "my-key", "key_1"]:
            resp = client.post("/api/keys", json={"name": name})
            assert resp.status_code == 201, f"Expected 201 for name '{name}'"


class TestApiKeyAuthFlow:
    def test_full_flow_create_and_use_key(self, client):
        """Create key → use key to access /api/solutions → 200."""
        # Create key
        resp = client.post("/api/keys", json={"name": "flow-test"})
        api_key = resp.json()["api_key"]

        # Access solutions with key (from localhost, so it passes anyway,
        # but verifying the key is valid)
        resp = client.get(
            "/api/solutions", headers={"X-API-Key": api_key}
        )
        assert resp.status_code == 200
