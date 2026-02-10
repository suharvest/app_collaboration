"""
Unit tests for Docker app configuration management feature.

Tests cover:
- Model changes (reconfigurable field, config_fields)
- Compose label config_file support
- Config manifest save/load
- get_app_config / update_app_config service logic
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from provisioning_station.models.device import UserInputConfig
from provisioning_station.models.docker_device import ManagedApp
from provisioning_station.utils.compose_labels import (
    LABELS,
    create_labels,
    parse_container_labels,
)

# ============================================
# Model Tests
# ============================================


class TestUserInputConfigReconfigurable:
    """Tests for UserInputConfig.reconfigurable field"""

    def test_reconfigurable_defaults_false(self):
        """reconfigurable defaults to False"""
        config = UserInputConfig(id="host", name="Host")
        assert config.reconfigurable is False

    def test_reconfigurable_set_true(self):
        """reconfigurable can be set to True"""
        config = UserInputConfig(id="host", name="Host", reconfigurable=True)
        assert config.reconfigurable is True

    def test_reconfigurable_in_model_dump(self):
        """reconfigurable appears in model serialization"""
        config = UserInputConfig(id="db_host", name="DB Host", reconfigurable=True)
        data = config.model_dump()
        assert "reconfigurable" in data
        assert data["reconfigurable"] is True

    def test_non_reconfigurable_not_exposed(self):
        """Non-reconfigurable fields should not be reconfigured"""
        password = UserInputConfig(
            id="password", name="SSH Password", type="password", reconfigurable=False
        )
        host = UserInputConfig(
            id="host", name="Host IP", type="text", reconfigurable=True
        )

        reconfigurable = [ui for ui in [password, host] if ui.reconfigurable]
        assert len(reconfigurable) == 1
        assert reconfigurable[0].id == "host"


class TestManagedAppConfigFields:
    """Tests for ManagedApp.config_fields field"""

    def test_config_fields_defaults_none(self):
        """config_fields defaults to None"""
        app = ManagedApp(solution_id="test", status="running")
        assert app.config_fields is None

    def test_config_fields_with_data(self):
        """config_fields can hold field definitions"""
        fields = [
            {"id": "db_host", "name": "Database Host", "current_value": "192.168.1.100"}
        ]
        app = ManagedApp(solution_id="test", status="running", config_fields=fields)
        assert app.config_fields == fields
        assert len(app.config_fields) == 1

    def test_config_fields_in_model_dump(self):
        """config_fields appears in model serialization"""
        app = ManagedApp(
            solution_id="test",
            status="running",
            config_fields=[{"id": "x", "name": "X"}],
        )
        data = app.model_dump()
        assert "config_fields" in data
        assert data["config_fields"] is not None

    def test_config_fields_none_in_dump(self):
        """config_fields is None when no fields set"""
        app = ManagedApp(solution_id="test", status="stopped")
        data = app.model_dump()
        assert data["config_fields"] is None


# ============================================
# Compose Labels Tests
# ============================================


class TestCreateLabelsConfigFile:
    """Tests for config_file support in create_labels"""

    def test_no_config_file_by_default(self):
        """config_file label not present when not provided"""
        labels = create_labels(solution_id="test", device_id="dev1")
        assert LABELS["config_file"] not in labels

    def test_config_file_included_when_provided(self):
        """config_file label included when argument passed"""
        labels = create_labels(
            solution_id="test",
            device_id="dev1",
            config_file="devices/backend.yaml",
        )
        assert labels[LABELS["config_file"]] == "devices/backend.yaml"

    def test_config_file_none_not_included(self):
        """config_file=None does not add label"""
        labels = create_labels(
            solution_id="test", device_id="dev1", config_file=None
        )
        assert LABELS["config_file"] not in labels


class TestParseContainerLabelsConfigFile:
    """Tests for config_file extraction in parse_container_labels"""

    def test_parses_config_file_when_present(self):
        """config_file extracted from labels"""
        labels = {
            LABELS["managed"]: "true",
            LABELS["solution_id"]: "heatmap",
            LABELS["config_file"]: "devices/docker.yaml",
        }
        result = parse_container_labels(labels)
        assert result is not None
        assert result["config_file"] == "devices/docker.yaml"

    def test_no_config_file_when_absent(self):
        """config_file not in result when label missing"""
        labels = {
            LABELS["managed"]: "true",
            LABELS["solution_id"]: "heatmap",
        }
        result = parse_container_labels(labels)
        assert result is not None
        assert "config_file" not in result


# ============================================
# Config Manifest Tests
# ============================================


class TestConfigManifest:
    """Tests for config manifest save/load via docker_device_manager"""

    @pytest.fixture
    def temp_manifests_dir(self, tmp_path):
        """Create a temp manifests directory simulating ~/.sensecraft/deployments/"""
        manifests_dir = tmp_path / "deployments" / "test_solution"
        manifests_dir.mkdir(parents=True)
        return manifests_dir

    @pytest.fixture
    def sample_manifest(self):
        """Return a sample config manifest"""
        return {
            "solution_id": "test_solution",
            "device_id": "backend",
            "device_type": "docker_local",
            "config_file": "devices/backend.yaml",
            "fields": [
                {
                    "id": "db_host",
                    "name": "Database Host",
                    "name_zh": "数据库地址",
                    "type": "text",
                    "current_value": "192.168.1.100",
                    "default": "localhost",
                    "required": True,
                    "placeholder": None,
                    "description": None,
                    "description_zh": None,
                    "validation": None,
                    "options": [],
                },
                {
                    "id": "api_endpoint",
                    "name": "API Endpoint",
                    "name_zh": "API 地址",
                    "type": "text",
                    "current_value": "http://api.example.com",
                    "default": "",
                    "required": False,
                    "placeholder": "https://...",
                    "description": None,
                    "description_zh": None,
                    "validation": None,
                    "options": [],
                },
            ],
        }

    def test_load_config_fields_returns_fields(
        self, temp_manifests_dir, sample_manifest
    ):
        """_load_config_fields returns fields from manifest files"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        # Write manifest
        manifest_path = temp_manifests_dir / "backend.json"
        manifest_path.write_text(json.dumps(sample_manifest))

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ):
            fields = docker_device_manager._load_config_fields("test_solution")

        assert fields is not None
        assert len(fields) == 2
        assert fields[0]["id"] == "db_host"
        assert fields[1]["id"] == "api_endpoint"

    def test_load_config_fields_returns_none_when_no_dir(self):
        """_load_config_fields returns None when dir doesn't exist"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        nonexistent = Path("/tmp/nonexistent_test_dir_abc123")
        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: nonexistent),
        ):
            fields = docker_device_manager._load_config_fields("missing")

        assert fields is None

    def test_load_config_fields_returns_none_when_empty(self, temp_manifests_dir):
        """_load_config_fields returns None when manifest has no fields"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        manifest = {"solution_id": "test", "device_id": "dev", "fields": []}
        (temp_manifests_dir / "dev.json").write_text(json.dumps(manifest))

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ):
            fields = docker_device_manager._load_config_fields("test")

        assert fields is None

    def test_load_config_fields_aggregates_multiple_manifests(
        self, temp_manifests_dir
    ):
        """_load_config_fields aggregates fields from multiple manifests"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        manifest1 = {
            "fields": [{"id": "field_a", "name": "Field A", "current_value": "a"}]
        }
        manifest2 = {
            "fields": [{"id": "field_b", "name": "Field B", "current_value": "b"}]
        }
        (temp_manifests_dir / "dev1.json").write_text(json.dumps(manifest1))
        (temp_manifests_dir / "dev2.json").write_text(json.dumps(manifest2))

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ):
            fields = docker_device_manager._load_config_fields("test")

        assert fields is not None
        assert len(fields) == 2
        ids = {f["id"] for f in fields}
        assert ids == {"field_a", "field_b"}


class TestGetAppConfig:
    """Tests for get_app_config method"""

    @pytest.fixture
    def temp_manifests_dir(self, tmp_path):
        manifests_dir = tmp_path / "deployments" / "heatmap"
        manifests_dir.mkdir(parents=True)
        return manifests_dir

    @pytest.mark.asyncio
    async def test_returns_none_when_no_manifests(self):
        """Returns None when no manifest directory exists"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        nonexistent = Path("/tmp/nonexistent_test_dir_xyz789")
        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: nonexistent),
        ):
            result = await docker_device_manager.get_app_config("missing")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_config_with_fields(self, temp_manifests_dir):
        """Returns config with aggregated fields"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        manifest = {
            "solution_id": "heatmap",
            "device_id": "server",
            "fields": [
                {"id": "influxdb_host", "name": "InfluxDB Host", "current_value": "192.168.1.50"}
            ],
        }
        (temp_manifests_dir / "server.json").write_text(json.dumps(manifest))

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ):
            result = await docker_device_manager.get_app_config("heatmap")

        assert result is not None
        assert result["solution_id"] == "heatmap"
        assert len(result["fields"]) == 1
        assert result["fields"][0]["id"] == "influxdb_host"
        assert result["fields"][0]["current_value"] == "192.168.1.50"

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_dir(self, temp_manifests_dir):
        """Returns None when directory exists but has no JSON files"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ):
            result = await docker_device_manager.get_app_config("heatmap")

        assert result is None


class TestUpdateAppConfig:
    """Tests for update_app_config method"""

    @pytest.fixture
    def temp_manifests_dir(self, tmp_path):
        manifests_dir = tmp_path / "deployments" / "test_sol"
        manifests_dir.mkdir(parents=True)
        return manifests_dir

    @pytest.mark.asyncio
    async def test_raises_when_no_manifests(self):
        """Raises RuntimeError when no manifest directory exists"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        nonexistent = Path("/tmp/nonexistent_test_dir_update_abc")
        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: nonexistent),
        ):
            with pytest.raises(RuntimeError, match="No config manifest"):
                await docker_device_manager.update_app_config("missing", {"key": "val"})

    @pytest.mark.asyncio
    async def test_calls_reconfigure_for_local_device(self, temp_manifests_dir):
        """Calls _reconfigure_local_device for docker_local manifests"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        manifest = {
            "solution_id": "test_sol",
            "device_id": "backend",
            "device_type": "docker_local",
            "config_file": "devices/backend.yaml",
            "fields": [
                {"id": "db_host", "name": "DB Host", "current_value": "old_ip"}
            ],
        }
        manifest_path = temp_manifests_dir / "backend.json"
        manifest_path.write_text(json.dumps(manifest))

        mock_reconfig = AsyncMock(
            return_value={"device_id": "backend", "success": True}
        )

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ), patch.object(
            docker_device_manager, "_reconfigure_local_device", mock_reconfig
        ):
            result = await docker_device_manager.update_app_config(
                "test_sol", {"db_host": "new_ip"}
            )

        assert result["success"] is True
        mock_reconfig.assert_called_once()
        call_args = mock_reconfig.call_args
        assert call_args[0][1] == {"db_host": "new_ip"}

    @pytest.mark.asyncio
    async def test_skips_non_local_devices(self, temp_manifests_dir):
        """Skips manifests that are not docker_local"""
        from provisioning_station.services.docker_device_manager import (
            docker_device_manager,
        )

        manifest = {
            "solution_id": "test_sol",
            "device_id": "remote_dev",
            "device_type": "docker_remote",
            "config_file": "devices/remote.yaml",
            "fields": [{"id": "host", "name": "Host", "current_value": "1.2.3.4"}],
        }
        (temp_manifests_dir / "remote_dev.json").write_text(json.dumps(manifest))

        mock_reconfig = AsyncMock()

        with patch.object(
            type(docker_device_manager),
            "_get_manifests_dir",
            staticmethod(lambda sid: temp_manifests_dir),
        ), patch.object(
            docker_device_manager, "_reconfigure_local_device", mock_reconfig
        ):
            result = await docker_device_manager.update_app_config(
                "test_sol", {"host": "5.6.7.8"}
            )

        # Should succeed but with no results (nothing to reconfigure locally)
        assert result["success"] is True
        mock_reconfig.assert_not_called()


# ============================================
# Deployment Engine Manifest Save Tests
# ============================================


class TestSaveConfigManifest:
    """Tests for _save_config_manifest in deployment_engine"""

    @pytest.fixture
    def engine(self):
        from provisioning_station.services.deployment_engine import DeploymentEngine
        return DeploymentEngine()

    @pytest.fixture
    def reconfigurable_config(self):
        """Config with reconfigurable user_inputs"""
        config = MagicMock()
        config.user_inputs = [
            UserInputConfig(
                id="db_host",
                name="Database Host",
                name_zh="数据库地址",
                type="text",
                default="localhost",
                required=True,
                reconfigurable=True,
            ),
            UserInputConfig(
                id="password",
                name="SSH Password",
                type="password",
                required=True,
                reconfigurable=False,
            ),
        ]
        return config

    @pytest.mark.asyncio
    async def test_saves_manifest_for_reconfigurable_fields(
        self, engine, reconfigurable_config, tmp_path
    ):
        """Only reconfigurable fields are saved in the manifest"""
        deploy_dir = tmp_path / ".sensecraft" / "deployments" / "my_solution"

        with patch("pathlib.Path.home", return_value=tmp_path):
            await engine._save_config_manifest(
                solution_id="my_solution",
                device_id="server",
                device_type="docker_local",
                config_file="devices/server.yaml",
                config=reconfigurable_config,
                connection={"db_host": "192.168.1.100", "password": "secret"},
            )

        manifest_path = deploy_dir / "server.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["solution_id"] == "my_solution"
        assert manifest["device_id"] == "server"
        assert manifest["device_type"] == "docker_local"
        assert manifest["config_file"] == "devices/server.yaml"
        assert len(manifest["fields"]) == 1  # Only db_host (reconfigurable)
        assert manifest["fields"][0]["id"] == "db_host"
        assert manifest["fields"][0]["current_value"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_skips_when_no_reconfigurable_fields(self, engine, tmp_path):
        """Does not save manifest when no reconfigurable fields exist"""
        config = MagicMock()
        config.user_inputs = [
            UserInputConfig(id="host", name="Host", reconfigurable=False),
        ]

        with patch("pathlib.Path.home", return_value=tmp_path):
            await engine._save_config_manifest(
                solution_id="test",
                device_id="dev",
                device_type="docker_local",
                config_file="devices/dev.yaml",
                config=config,
                connection={"host": "1.2.3.4"},
            )

        deploy_dir = tmp_path / ".sensecraft" / "deployments" / "test"
        assert not deploy_dir.exists()

    @pytest.mark.asyncio
    async def test_skips_when_no_user_inputs(self, engine, tmp_path):
        """Does not save manifest when user_inputs is empty"""
        config = MagicMock()
        config.user_inputs = []

        with patch("pathlib.Path.home", return_value=tmp_path):
            await engine._save_config_manifest(
                solution_id="test",
                device_id="dev",
                device_type="docker_local",
                config_file="devices/dev.yaml",
                config=config,
                connection={},
            )

        deploy_dir = tmp_path / ".sensecraft" / "deployments" / "test"
        assert not deploy_dir.exists()

    @pytest.mark.asyncio
    async def test_uses_default_when_value_not_in_connection(
        self, engine, tmp_path
    ):
        """Uses default value when field not found in connection dict"""
        config = MagicMock()
        config.user_inputs = [
            UserInputConfig(
                id="port",
                name="Port",
                type="text",
                default="8080",
                reconfigurable=True,
            ),
        ]

        with patch("pathlib.Path.home", return_value=tmp_path):
            await engine._save_config_manifest(
                solution_id="test",
                device_id="dev",
                device_type="docker_local",
                config_file="devices/dev.yaml",
                config=config,
                connection={},  # port not in connection
            )

        deploy_dir = tmp_path / ".sensecraft" / "deployments" / "test"
        manifest = json.loads((deploy_dir / "dev.json").read_text())
        assert manifest["fields"][0]["current_value"] == "8080"
