"""
Unit tests for API Key Manager
"""

import json

import pytest

from provisioning_station.services.api_key_manager import ApiKeyManager


@pytest.fixture
def manager(tmp_path):
    """Create an ApiKeyManager using a temp directory."""
    return ApiKeyManager(data_dir=tmp_path)


class TestApiKeyManager:
    def test_create_key_returns_ps_prefix(self, manager):
        """create_key() returns a key starting with ps_"""
        key = manager.create_key("test")
        assert key.startswith("ps_")
        assert len(key) > 10

    def test_create_key_unique(self, manager):
        """Two create_key() calls return different keys."""
        key1 = manager.create_key("a")
        key2 = manager.create_key("b")
        assert key1 != key2

    def test_validate_valid_key(self, manager):
        """validate_key() returns a record dict for a valid key."""
        key = manager.create_key("mykey")
        record = manager.validate_key(key)
        assert record is not None
        assert record["name"] == "mykey"
        assert "created_at" in record

    def test_validate_invalid_key(self, manager):
        """validate_key() returns None for an invalid key."""
        assert manager.validate_key("ps_invalid") is None

    def test_validate_updates_last_used(self, manager):
        """validate_key() updates last_used_at on success."""
        key = manager.create_key("k")
        # Before first validate, last_used is None in storage
        keys = manager.list_keys()
        assert keys[0]["last_used_at"] is None

        manager.validate_key(key)
        keys = manager.list_keys()
        assert keys[0]["last_used_at"] is not None

    def test_list_keys_no_hash(self, manager):
        """list_keys() returns name/created_at/last_used_at/id, not key_hash."""
        manager.create_key("x")
        keys = manager.list_keys()
        assert len(keys) == 1
        assert "name" in keys[0]
        assert "id" in keys[0]
        assert "created_at" in keys[0]
        assert "last_used_at" in keys[0]
        assert "key_hash" not in keys[0]

    def test_delete_key(self, manager):
        """delete_key() removes the key; validate afterwards returns None."""
        key = manager.create_key("del")
        assert manager.delete_key("del") is True
        assert manager.validate_key(key) is None

    def test_delete_nonexistent_key(self, manager):
        """delete_key() returns False for a name that doesn't exist."""
        assert manager.delete_key("nope") is False

    def test_persistence(self, tmp_path):
        """A new manager instance can read keys written by a previous one."""
        m1 = ApiKeyManager(data_dir=tmp_path)
        key = m1.create_key("persist")

        m2 = ApiKeyManager(data_dir=tmp_path)
        assert m2.validate_key(key) is not None

    def test_ensure_default_key_creates_when_empty(self, manager):
        """With no keys, ensure_default_key() creates 'default' and returns plaintext."""
        key = manager.ensure_default_key()
        assert key is not None
        assert key.startswith("ps_")
        keys = manager.list_keys()
        assert any(k["name"] == "default" for k in keys)

    def test_ensure_default_key_noop_when_exists(self, manager):
        """With existing keys, ensure_default_key() returns None."""
        manager.create_key("existing")
        assert manager.ensure_default_key() is None


class TestNameValidation:
    def test_valid_names(self, manager):
        """Alphanumeric, dash, underscore names are accepted."""
        for name in ["test", "my-key", "key_1", "A", "a" * 64]:
            key = manager.create_key(name)
            assert key.startswith("ps_")

    def test_empty_name_rejected(self, manager):
        with pytest.raises(ValueError, match="Invalid key name"):
            manager.create_key("")

    def test_space_in_name_rejected(self, manager):
        with pytest.raises(ValueError, match="Invalid key name"):
            manager.create_key("my key")

    def test_special_chars_rejected(self, manager):
        for bad in ["key!", "a/b", "x@y", "../etc", "a b", "k\n"]:
            with pytest.raises(ValueError, match="Invalid key name"):
                manager.create_key(bad)

    def test_too_long_name_rejected(self, manager):
        with pytest.raises(ValueError, match="Invalid key name"):
            manager.create_key("a" * 65)

    def test_duplicate_name_rejected(self, manager):
        """Creating a key with the same name twice raises ValueError."""
        manager.create_key("dup")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_key("dup")


class TestIdField:
    def test_create_key_has_id(self, manager):
        """Newly created keys have a UUID id."""
        manager.create_key("withid")
        keys = manager.list_keys()
        assert len(keys[0]["id"]) == 36  # UUID format

    def test_delete_key_by_id(self, manager):
        """delete_key_by_id() removes the correct key."""
        manager.create_key("k1")
        manager.create_key("k2")
        keys = manager.list_keys()
        k1_id = keys[0]["id"]

        assert manager.delete_key_by_id(k1_id) is True
        remaining = manager.list_keys()
        assert len(remaining) == 1
        assert remaining[0]["name"] == "k2"

    def test_delete_key_by_id_nonexistent(self, manager):
        assert manager.delete_key_by_id("00000000-0000-0000-0000-000000000000") is False

    def test_delete_key_by_name_only_deletes_first(self, tmp_path):
        """delete_key(name) should only remove the first match.

        This tests the fix: old code used list comprehension which deleted all matches.
        We simulate by writing two records with the same name directly.
        """
        m = ApiKeyManager(data_dir=tmp_path)
        # Write two records with same name (bypassing create_key validation)
        m._keys = [
            {"id": "id-1", "name": "dup", "key_hash": "h1", "created_at": "t1", "last_used_at": None},
            {"id": "id-2", "name": "dup", "key_hash": "h2", "created_at": "t2", "last_used_at": None},
        ]
        m._save()

        assert m.delete_key("dup") is True
        assert len(m._keys) == 1
        assert m._keys[0]["id"] == "id-2"  # First was deleted, second remains


class TestMigration:
    def test_old_records_get_id_on_load(self, tmp_path):
        """Records without 'id' get a UUID assigned on load."""
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps([
            {"name": "old", "key_hash": "abc123", "created_at": "2024-01-01", "last_used_at": None},
        ]))

        m = ApiKeyManager(data_dir=tmp_path)
        keys = m.list_keys()
        assert len(keys) == 1
        assert "id" in keys[0]
        assert len(keys[0]["id"]) == 36

        # Verify saved to disk
        raw = json.loads(keys_file.read_text())
        assert "id" in raw[0]

    def test_migration_preserves_existing_id(self, tmp_path):
        """Records that already have 'id' are not overwritten."""
        original_id = "11111111-1111-1111-1111-111111111111"
        keys_file = tmp_path / "api_keys.json"
        keys_file.write_text(json.dumps([
            {"id": original_id, "name": "new", "key_hash": "def456", "created_at": "2024-06-01", "last_used_at": None},
        ]))

        m = ApiKeyManager(data_dir=tmp_path)
        assert m.list_keys()[0]["id"] == original_id
