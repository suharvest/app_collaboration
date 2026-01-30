"""
Shared constants and utilities between frontend and backend.

This module contains values that MUST be kept in sync between
the frontend JavaScript and backend Python code.
"""

from .constants import (
    DEFAULT_PORT,
    API_VERSION,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    REQUEST_TIMEOUT_MS,
)

__all__ = [
    "DEFAULT_PORT",
    "API_VERSION",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "REQUEST_TIMEOUT_MS",
]
