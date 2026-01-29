"""
Shared pytest fixtures for provisioning station tests
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import yaml
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_solution_yaml() -> dict:
    """Return minimal valid solution YAML data for testing"""
    return {
        "version": "1.0",
        "id": "test_solution",
        "name": "Test Solution",
        "name_zh": "测试方案",
        "intro": {
            "summary": "A test solution for unit testing",
            "summary_zh": "用于单元测试的测试方案",
            "description_file": "intro/description.md",
            "description_file_zh": "intro/description_zh.md",
            "category": "testing",
            "tags": ["test", "unit-test"],
            "stats": {
                "difficulty": "beginner",
                "estimated_time": "10min",
                "deployed_count": 0,
                "likes_count": 0,
            },
        },
        "deployment": {
            "guide_file": "deploy/guide.md",
            "guide_file_zh": "deploy/guide_zh.md",
            "devices": [],
            "order": [],
        },
    }


@pytest.fixture
def temp_solutions_dir(test_solution_yaml: dict) -> Generator[Path, None, None]:
    """Create a temporary solutions directory with a test solution"""
    with tempfile.TemporaryDirectory() as tmpdir:
        solutions_dir = Path(tmpdir) / "solutions"
        solutions_dir.mkdir()

        # Create test solution
        test_solution_path = solutions_dir / "test_solution"
        test_solution_path.mkdir()

        # Create subdirectories
        (test_solution_path / "intro" / "gallery").mkdir(parents=True)
        (test_solution_path / "deploy" / "sections").mkdir(parents=True)

        # Write solution.yaml
        with open(test_solution_path / "solution.yaml", "w", encoding="utf-8") as f:
            yaml.dump(test_solution_yaml, f, allow_unicode=True)

        # Create markdown files
        with open(test_solution_path / "intro" / "description.md", "w", encoding="utf-8") as f:
            f.write("# Test Solution\n\nThis is a test solution for testing purposes.\n")

        with open(test_solution_path / "intro" / "description_zh.md", "w", encoding="utf-8") as f:
            f.write("# 测试方案\n\n这是一个用于测试目的的测试方案。\n")

        with open(test_solution_path / "deploy" / "guide.md", "w", encoding="utf-8") as f:
            f.write("## Deployment Guide\n\nFollow these steps to deploy.\n")

        with open(test_solution_path / "deploy" / "guide_zh.md", "w", encoding="utf-8") as f:
            f.write("## 部署指南\n\n按照以下步骤部署。\n")

        yield solutions_dir


@pytest.fixture
def sample_compose_content() -> str:
    """Return sample docker-compose.yml content"""
    return """version: '3.8'
services:
  webapp:
    image: nginx:latest
    ports:
      - "80:80"
  database:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
"""


@pytest.fixture
def sample_compose_with_labels() -> str:
    """Return sample docker-compose.yml content with existing labels"""
    return """version: '3.8'
services:
  webapp:
    image: nginx:latest
    labels:
      - "com.example.app=webapp"
    ports:
      - "80:80"
"""


@pytest.fixture
def sample_compose_labels_list() -> str:
    """Return sample docker-compose.yml content with labels as list"""
    return """version: '3.8'
services:
  webapp:
    image: nginx:latest
    labels:
      - "existing.label=value"
      - "another.label=value2"
"""


# FastAPI test client fixtures
@pytest.fixture
def app():
    """Create FastAPI app for testing"""
    from provisioning_station.main import create_app
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create sync test client"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
