"""
API Key management for external API access.

Keys are stored as SHA-256 hashes in data/api_keys.json.
The plaintext key is only returned once at creation time.
"""

import hashlib
import json
import logging
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ..config import settings

logger = logging.getLogger(__name__)

KEY_PREFIX = "ps_"
KEY_BYTES = 32  # 256 bits of entropy
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,64}\Z")


class ApiKeyManager:
    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or settings.data_dir
        self._keys_file = self._data_dir / "api_keys.json"
        self._keys: list[dict] = []
        self._load()

    def _load(self):
        if self._keys_file.exists():
            try:
                self._keys = json.loads(self._keys_file.read_text())
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load api_keys.json: %s", e)
                self._keys = []
        else:
            self._keys = []

        # Auto-migrate: add missing "id" fields to old records
        migrated = False
        for record in self._keys:
            if "id" not in record:
                record["id"] = str(uuid4())
                migrated = True
        if migrated:
            self._save()

    def _save(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._keys_file.write_text(json.dumps(self._keys, indent=2))

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate key name. Raises ValueError if invalid."""
        if not NAME_PATTERN.match(name):
            raise ValueError(
                f"Invalid key name '{name}': must match [a-zA-Z0-9_-]{{1,64}}"
            )

    def create_key(self, name: str) -> str:
        """Create a new API key. Returns the plaintext key (shown only once).

        Raises ValueError if name is invalid or already exists.
        """
        self._validate_name(name)

        if any(r["name"] == name for r in self._keys):
            raise ValueError(f"Key name '{name}' already exists")

        raw = secrets.token_hex(KEY_BYTES)
        plaintext = f"{KEY_PREFIX}{raw}"
        now = datetime.now(timezone.utc).isoformat()

        self._keys.append(
            {
                "id": str(uuid4()),
                "name": name,
                "key_hash": self._hash_key(plaintext),
                "created_at": now,
                "last_used_at": None,
            }
        )
        self._save()
        logger.info("Created API key '%s'", name)
        return plaintext

    def validate_key(self, key: str) -> Optional[dict]:
        """Validate an API key. Returns the key record (without hash) or None."""
        key_hash = self._hash_key(key)
        for record in self._keys:
            if record["key_hash"] == key_hash:
                record["last_used_at"] = datetime.now(timezone.utc).isoformat()
                self._save()
                return {
                    "name": record["name"],
                    "created_at": record["created_at"],
                    "last_used_at": record["last_used_at"],
                }
        return None

    def list_keys(self) -> list[dict]:
        """List all keys (without hashes)."""
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "last_used_at": r["last_used_at"],
            }
            for r in self._keys
        ]

    def delete_key(self, name: str) -> bool:
        """Delete the first key matching name. Returns True if found and deleted."""
        for i, r in enumerate(self._keys):
            if r["name"] == name:
                self._keys.pop(i)
                self._save()
                logger.info("Deleted API key '%s'", name)
                return True
        return False

    def delete_key_by_id(self, key_id: str) -> bool:
        """Delete a key by its UUID id. Returns True if found and deleted."""
        for i, r in enumerate(self._keys):
            if r["id"] == key_id:
                name = r["name"]
                self._keys.pop(i)
                self._save()
                logger.info("Deleted API key '%s' (id=%s)", name, key_id)
                return True
        return False

    def ensure_default_key(self) -> Optional[str]:
        """If no keys exist, create a 'default' key and return its plaintext."""
        if self._keys:
            return None
        return self.create_key("default")


# Module-level singleton (lazy init)
_manager: Optional[ApiKeyManager] = None


def get_api_key_manager() -> ApiKeyManager:
    global _manager
    if _manager is None:
        _manager = ApiKeyManager()
    return _manager
