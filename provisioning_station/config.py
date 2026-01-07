"""
Application configuration using pydantic-settings
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application info
    app_name: str = "Provisioning Station"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server settings
    host: str = "127.0.0.1"
    port: int = 3260

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    solutions_dir: Path = base_dir / "solutions"
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
