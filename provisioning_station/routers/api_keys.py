"""
API Key management endpoints.

All endpoints are localhost-only (enforced by auth middleware).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import settings
from ..services.api_key_manager import get_api_key_manager

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


class CreateKeyRequest(BaseModel):
    name: str


class CreateKeyResponse(BaseModel):
    name: str
    api_key: str


@router.post("", response_model=CreateKeyResponse, status_code=201)
async def create_key(body: CreateKeyRequest):
    """Create a new API key. The key is returned only once."""
    manager = get_api_key_manager()
    try:
        plaintext = manager.create_key(body.name)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return CreateKeyResponse(name=body.name, api_key=plaintext)


@router.get("")
async def list_keys():
    """List all API keys (without secrets)."""
    manager = get_api_key_manager()
    return {"keys": manager.list_keys()}


@router.delete("/id/{key_id}")
async def delete_key_by_id(key_id: str):
    """Delete an API key by its UUID id."""
    manager = get_api_key_manager()
    if not manager.delete_key_by_id(key_id):
        raise HTTPException(status_code=404, detail=f"Key id '{key_id}' not found")
    return {"status": "deleted", "id": key_id}


@router.delete("/{name}")
async def delete_key(name: str):
    """Delete an API key by name."""
    manager = get_api_key_manager()
    if not manager.delete_key(name):
        raise HTTPException(status_code=404, detail=f"Key '{name}' not found")
    return {"status": "deleted", "name": name}


@router.get("/status")
async def api_status():
    """Get API access status."""
    manager = get_api_key_manager()
    return {
        "api_enabled": settings.api_enabled,
        "key_count": len(manager.list_keys()),
    }
