"""
Integration tests for Solutions API endpoints
"""

import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from provisioning_station.models.solution import Solution, SolutionIntro, SolutionDeployment, SolutionStats


@pytest.fixture
def mock_solution():
    """Create a mock solution for testing"""
    return Solution(
        id="test_solution",
        name="Test Solution",
        name_zh="测试方案",
        base_path="/tmp/test_solution",
        intro=SolutionIntro(
            summary="A test solution",
            summary_zh="测试方案描述",
            description_file="intro/description.md",
            description_file_zh="intro/description_zh.md",
            category="testing",
            tags=["test", "demo"],
            stats=SolutionStats(
                difficulty="beginner",
                estimated_time="10min",
                deployed_count=5,
                likes_count=10
            )
        ),
        deployment=SolutionDeployment(
            guide_file="deploy/guide.md",
            guide_file_zh="deploy/guide_zh.md"
        )
    )


@pytest.fixture
def mock_solution_manager(mock_solution):
    """Create a mock solution manager"""
    from provisioning_station.services.solution_manager import SolutionManager

    manager = SolutionManager()
    manager.solutions = {"test_solution": mock_solution}
    manager._global_device_catalog = {}
    return manager


class TestListSolutions:
    """Tests for GET /api/solutions/"""

    def test_list_solutions_empty(self):
        """Test listing solutions when none exist"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_all_solutions', return_value=[]):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/solutions/")

                assert response.status_code == 200
                assert response.json() == []

    def test_list_solutions_with_solutions(self, mock_solution):
        """Test listing solutions with existing solutions"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_all_solutions', return_value=[mock_solution]):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=2):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.get("/api/solutions/")

                    assert response.status_code == 200
                    data = response.json()
                    assert len(data) == 1
                    assert data[0]["id"] == "test_solution"
                    assert data[0]["name"] == "Test Solution"

    def test_list_solutions_filter_by_category(self, mock_solution):
        """Test filtering solutions by category"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_all_solutions', return_value=[mock_solution]):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=0):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    # Filter by matching category
                    response = client.get("/api/solutions/?category=testing")
                    assert response.status_code == 200
                    assert len(response.json()) == 1

                    # Filter by non-matching category
                    response = client.get("/api/solutions/?category=voice_ai")
                    assert response.status_code == 200
                    assert len(response.json()) == 0


class TestGetSolution:
    """Tests for GET /api/solutions/{solution_id}"""

    def test_get_solution_exists(self, mock_solution):
        """Test getting an existing solution"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_solution', return_value=mock_solution):
            with patch.object(solution_manager, 'load_markdown', new_callable=AsyncMock, return_value="<p>Description</p>"):
                with patch.object(solution_manager, 'get_all_devices_from_solution', return_value=[]):
                    with patch.object(solution_manager, 'get_global_device_catalog', return_value={}):
                        from provisioning_station.main import app
                        with TestClient(app, raise_server_exceptions=False) as client:
                            response = client.get("/api/solutions/test_solution")

                            assert response.status_code == 200
                            data = response.json()
                            assert data["id"] == "test_solution"
                            assert data["name"] == "Test Solution"
                            assert data["category"] == "testing"

    def test_get_solution_not_found(self):
        """Test getting a non-existent solution"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_solution', return_value=None):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/solutions/nonexistent")

                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()

    def test_get_solution_with_lang_zh(self, mock_solution):
        """Test getting solution with Chinese language"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_solution', return_value=mock_solution):
            with patch.object(solution_manager, 'load_markdown', new_callable=AsyncMock, return_value="<p>中文描述</p>"):
                with patch.object(solution_manager, 'get_all_devices_from_solution', return_value=[]):
                    with patch.object(solution_manager, 'get_global_device_catalog', return_value={}):
                        from provisioning_station.main import app
                        with TestClient(app, raise_server_exceptions=False) as client:
                            response = client.get("/api/solutions/test_solution?lang=zh")

                            assert response.status_code == 200
                            data = response.json()
                            assert data["name"] == "测试方案"


class TestGetDeploymentInfo:
    """Tests for GET /api/solutions/{solution_id}/deployment"""

    def test_get_deployment_info(self, mock_solution):
        """Test getting deployment information"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_solution', return_value=mock_solution):
            with patch.object(solution_manager, 'load_markdown', new_callable=AsyncMock, return_value="<p>Guide</p>"):
                with patch.object(solution_manager, 'get_all_devices_from_solution', return_value=[]):
                    from provisioning_station.main import app
                    with TestClient(app, raise_server_exceptions=False) as client:
                        response = client.get("/api/solutions/test_solution/deployment")

                        assert response.status_code == 200
                        data = response.json()
                        assert data["solution_id"] == "test_solution"
                        assert "guide" in data

    def test_get_deployment_info_not_found(self):
        """Test getting deployment info for non-existent solution"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_solution', return_value=None):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/solutions/nonexistent/deployment")

                assert response.status_code == 404


class TestHealthCheck:
    """Tests for GET /api/health"""

    def test_health_check(self):
        """Test health check endpoint"""
        from provisioning_station.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "version" in data


class TestSolutionCRUD:
    """Tests for Solution CRUD endpoints"""

    def test_create_solution(self, mock_solution):
        """Test creating a new solution"""
        from provisioning_station.services.solution_manager import solution_manager

        async def mock_create(data):
            return mock_solution

        with patch.object(solution_manager, 'create_solution', new_callable=AsyncMock, side_effect=mock_create):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=0):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.post("/api/solutions/", json={
                        "id": "new_solution",
                        "name": "New Solution",
                        "summary": "A new solution"
                    })

                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == "test_solution"

    def test_create_solution_invalid_id(self):
        """Test creating solution with invalid ID"""
        from provisioning_station.services.solution_manager import solution_manager

        async def mock_create(data):
            raise ValueError("Invalid solution ID format")

        with patch.object(solution_manager, 'create_solution', new_callable=AsyncMock, side_effect=mock_create):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post("/api/solutions/", json={
                    "id": "Invalid-ID",
                    "name": "Test",
                    "summary": "Test"
                })

                assert response.status_code == 400

    def test_update_solution(self, mock_solution):
        """Test updating a solution"""
        from provisioning_station.services.solution_manager import solution_manager

        # Create updated solution
        updated_solution = Solution(
            id="test_solution",
            name="Updated Solution",
            name_zh="更新的方案",
            base_path="/tmp/test",
            intro=mock_solution.intro,
            deployment=mock_solution.deployment
        )

        async def mock_update(solution_id, data):
            return updated_solution

        with patch.object(solution_manager, 'update_solution', new_callable=AsyncMock, side_effect=mock_update):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=0):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.put("/api/solutions/test_solution", json={
                        "name": "Updated Solution"
                    })

                    assert response.status_code == 200
                    data = response.json()
                    assert data["name"] == "Updated Solution"

    def test_delete_solution(self):
        """Test deleting a solution"""
        from provisioning_station.services.solution_manager import solution_manager

        async def mock_delete(solution_id, move_to_trash=True):
            return True

        with patch.object(solution_manager, 'delete_solution', new_callable=AsyncMock, side_effect=mock_delete):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.delete("/api/solutions/test_solution")

                assert response.status_code == 200
                assert response.json()["success"] is True

    def test_delete_solution_not_found(self):
        """Test deleting non-existent solution"""
        from provisioning_station.services.solution_manager import solution_manager

        async def mock_delete(solution_id, move_to_trash=True):
            raise ValueError("Solution not found")

        with patch.object(solution_manager, 'delete_solution', new_callable=AsyncMock, side_effect=mock_delete):
            from provisioning_station.main import app
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.delete("/api/solutions/nonexistent")

                assert response.status_code == 404


class TestLangParameter:
    """Tests for language parameter validation"""

    def test_valid_lang_en(self, mock_solution):
        """Test valid English language parameter"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_all_solutions', return_value=[mock_solution]):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=0):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.get("/api/solutions/?lang=en")
                    assert response.status_code == 200

    def test_valid_lang_zh(self, mock_solution):
        """Test valid Chinese language parameter"""
        from provisioning_station.services.solution_manager import solution_manager

        with patch.object(solution_manager, 'get_all_solutions', return_value=[mock_solution]):
            with patch.object(solution_manager, 'count_devices_in_solution', return_value=0):
                from provisioning_station.main import app
                with TestClient(app, raise_server_exceptions=False) as client:
                    response = client.get("/api/solutions/?lang=zh")
                    assert response.status_code == 200

    def test_invalid_lang(self):
        """Test invalid language parameter"""
        from provisioning_station.main import app
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/solutions/?lang=invalid")
            assert response.status_code == 422  # Validation error
