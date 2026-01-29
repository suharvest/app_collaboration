"""
Application configuration using pydantic-settings
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


def _get_default_solutions_dir() -> Path:
    """Get default solutions directory, checking multiple locations."""
    # 1. Environment variable (highest priority, handled by pydantic)
    # 2. Relative to executable (for Tauri bundled app)
    # 3. Relative to source (for development)

    import sys as _sys

    base_dir = Path(__file__).parent.parent

    # Check if running as bundled app (PyInstaller)
    if getattr(_sys, "frozen", False):
        # Running as compiled executable
        exe_dir = Path(_sys.executable).parent

        # Tauri puts resources in different locations per platform:
        # - macOS: .app/Contents/Resources/_up_/solutions
        # - Windows: app_dir/_up_/solutions or app_dir/resources/solutions
        # - Linux: app_dir/_up_/solutions
        candidates = [
            # Tauri v2 resource path pattern (all platforms)
            exe_dir.parent / "Resources" / "_up_" / "solutions",  # macOS .app bundle
            exe_dir / "_up_" / "solutions",  # Windows/Linux Tauri v2
            # Legacy patterns
            exe_dir.parent / "Resources" / "solutions",  # macOS legacy
            exe_dir / "resources" / "solutions",  # Windows alternative
            exe_dir / "solutions",  # Same directory fallback
            # Windows NSIS installer pattern
            exe_dir.parent / "resources" / "_up_" / "solutions",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Log warning if no candidate found in bundled mode
        import logging

        logging.getLogger(__name__).warning(
            f"Solutions directory not found in bundled app. "
            f"Tried: {[str(c) for c in candidates]}"
        )

    # Development mode - relative to source
    return base_dir / "solutions"


class Settings(BaseSettings):
    """Application settings"""

    # Application info
    app_name: str = "Provisioning Station"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server settings
    host: str = "127.0.0.1"
    port: int = 3260

    # Paths - solutions_dir can be overridden via PS_SOLUTIONS_DIR env var
    base_dir: Path = Path(__file__).parent.parent
    solutions_dir: Path = _get_default_solutions_dir()
    data_dir: Path = base_dir / "data"
    logs_dir: Path = data_dir / "logs"
    cache_dir: Path = data_dir / "cache"

    # Language
    default_language: str = "zh"  # zh | en

    # Solution source (for future remote support)
    solution_source: str = "local"  # local | remote
    solution_remote_url: Optional[str] = None

    class Config:
        env_prefix = "PS_"
        env_file = ".env"


settings = Settings()
