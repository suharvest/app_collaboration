"""
Unit tests for HAIntegrationDeployer config helpers.
"""

import pytest

from provisioning_station.deployers.ha_integration_deployer import (
    HAIntegrationDeployer,
)
from provisioning_station.models.device import (
    ConfigFlowField,
    DeviceConfig,
    HAIntegrationConfig,
)


@pytest.fixture
def deployer():
    return HAIntegrationDeployer()


def _make_config(
    domain="recamera",
    components_dir="assets/docker/custom_components/recamera",
    config_flow_data=None,
    include_patterns=None,
):
    """Helper to create a DeviceConfig with ha_integration."""
    ha_cfg = HAIntegrationConfig(
        domain=domain,
        components_dir=components_dir,
        **({"config_flow_data": config_flow_data} if config_flow_data else {}),
        **({"include_patterns": include_patterns} if include_patterns else {}),
    )
    return DeviceConfig(
        id="test",
        name="Test",
        type="ha_integration",
        ha_integration=ha_cfg,
    )


# --- HAIntegrationConfig model tests ---


class TestHAIntegrationConfig:
    def test_minimal_config(self):
        cfg = HAIntegrationConfig(
            domain="recamera",
            components_dir="assets/docker/custom_components/recamera",
        )
        assert cfg.domain == "recamera"
        assert cfg.config_flow_data == []
        assert "*.py" in cfg.include_patterns

    def test_config_flow_data(self):
        cfg = HAIntegrationConfig(
            domain="my_sensor",
            components_dir="assets/custom_components/my_sensor",
            config_flow_data=[
                ConfigFlowField(name="host", value_from="sensor_ip"),
                ConfigFlowField(name="port", value_from="sensor_port", type="int"),
            ],
        )
        assert len(cfg.config_flow_data) == 2
        assert cfg.config_flow_data[1].type == "int"

    def test_custom_include_patterns(self):
        cfg = HAIntegrationConfig(
            domain="my_sensor",
            components_dir="assets/my_sensor",
            include_patterns=["*.py", "manifest.json", "translations/*.json"],
        )
        assert "translations/*.json" in cfg.include_patterns

    def test_device_config_accepts_ha_integration(self):
        dc = DeviceConfig(
            id="test",
            name="Test",
            type="ha_integration",
            ha_integration=HAIntegrationConfig(
                domain="my_integration",
                components_dir="assets/custom_components/my_integration",
            ),
        )
        assert dc.ha_integration.domain == "my_integration"


# --- Deployer helper tests ---


class TestGetDomain:
    def test_returns_domain_from_config(self, deployer):
        config = _make_config(domain="my_custom")
        assert deployer._get_domain(config) == "my_custom"

    def test_raises_without_ha_integration(self, deployer):
        config = DeviceConfig(id="test", name="Test", type="ha_integration")
        with pytest.raises(RuntimeError, match="ha_integration"):
            deployer._get_domain(config)


class TestGetIncludePatterns:
    def test_returns_config_patterns(self, deployer):
        config = _make_config(include_patterns=["*.py", "translations/*.json"])
        assert deployer._get_include_patterns(config) == [
            "*.py",
            "translations/*.json",
        ]

    def test_returns_defaults(self, deployer):
        config = _make_config()
        patterns = deployer._get_include_patterns(config)
        assert "*.py" in patterns
        assert "manifest.json" in patterns


class TestBuildConfigFlowData:
    def test_value_from_connection(self, deployer):
        config = _make_config(
            config_flow_data=[
                ConfigFlowField(name="host", value_from="device_ip"),
                ConfigFlowField(name="port", value_from="device_port", type="int"),
            ]
        )
        connection = {"device_ip": "10.0.0.1", "device_port": "8080"}
        result = deployer._build_config_flow_data(config, connection)
        assert result == {"host": "10.0.0.1", "port": 8080}

    def test_static_value(self, deployer):
        config = _make_config(
            config_flow_data=[
                ConfigFlowField(name="mode", value="auto"),
            ]
        )
        result = deployer._build_config_flow_data(config, {})
        assert result == {"mode": "auto"}

    def test_bool_type(self, deployer):
        config = _make_config(
            config_flow_data=[
                ConfigFlowField(name="enabled", value="true", type="bool"),
            ]
        )
        result = deployer._build_config_flow_data(config, {})
        assert result == {"enabled": True}

    def test_empty_config_flow_data(self, deployer):
        config = _make_config()
        result = deployer._build_config_flow_data(config, {})
        assert result == {}


class TestGetComponentsPath:
    def test_returns_none_without_ha_integration(self, deployer):
        config = DeviceConfig(id="test", name="Test", type="ha_integration")
        assert deployer._get_components_path(config) is None

    def test_resolves_existing_path(self, deployer, tmp_path):
        comp_dir = tmp_path / "assets" / "custom_components" / "my_thing"
        comp_dir.mkdir(parents=True)
        config = _make_config(
            components_dir="assets/custom_components/my_thing",
        )
        config.base_path = str(tmp_path)
        result = deployer._get_components_path(config)
        assert result == str(comp_dir)

    def test_returns_none_for_missing_dir(self, deployer, tmp_path):
        config = _make_config(
            components_dir="assets/nonexistent",
        )
        config.base_path = str(tmp_path)
        assert deployer._get_components_path(config) is None


class TestBuildTar:
    def test_packs_matching_files(self, deployer, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "sensor.py").write_text("")
        (tmp_path / "manifest.json").write_text("{}")
        (tmp_path / "README.md").write_text("ignore me")

        b64_data, files = deployer._build_tar(
            str(tmp_path), ["*.py", "manifest.json"]
        )
        assert "manifest.json" in files
        assert "__init__.py" in files
        assert "sensor.py" in files
        assert "README.md" not in files

    def test_raises_on_empty_dir(self, deployer, tmp_path):
        with pytest.raises(RuntimeError, match="No component files"):
            deployer._build_tar(str(tmp_path), ["*.py"])
