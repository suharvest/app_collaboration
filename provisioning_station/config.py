"""
Application configuration using pydantic-settings
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


def _get_default_solutions_dir() -> Path:
    """Get default solutions directory, checking multiple locations."""
    # 1. Environment variable (highest priority, handled by pydantic)
    # 2. Relative to executable (for Tauri bundled app)
    # 3. Relative to source (for development)

    base_dir = Path(__file__).parent.parent

    # Check if running as bundled app (PyInstaller)
    if getattr(os.sys, 'frozen', False):
        # Running as compiled executable
        exe_dir = Path(os.sys.executable).parent
        # Tauri puts resources in ../Resources on macOS, same dir on Windows/Linux
        candidates = [
            exe_dir.parent / "Resources" / "solutions",  # macOS .app bundle
            exe_dir / "solutions",  # Windows/Linux
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

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
