"""
Unit tests for Node-RED module management in NodeRedDeployer._ensure_modules
"""

import importlib
import sys
import types
from unittest.mock import AsyncMock, patch

import pytest

from provisioning_station.models.device import (
    DeviceConfig,
    NodeRedConfig,
    NodeRedModuleConfig,
)


def _import_nodered_deployer():
    """Import nodered_deployer module without triggering deployers/__init__.py."""
    mod_name = "provisioning_station.deployers.nodered_deployer"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    parent = "provisioning_station.deployers"
    parent_was_missing = parent not in sys.modules
    if parent_was_missing:
        pkg = types.ModuleType(parent)
        pkg.__path__ = [
            str(importlib.import_module("provisioning_station").__path__[0])
            + "/deployers"
        ]
        pkg.__package__ = parent
        sys.modules[parent] = pkg
    mod = importlib.import_module(mod_name)
    return mod


class FakeResponse:
    """Minimal httpx response stub."""

    def __init__(self, status_code: int = 200, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


def _make_nodes_response(modules: dict[str, str]) -> list[dict]:
    """Build a Node-RED /nodes response from {name: version} dict."""
    return [{"module": name, "version": ver} for name, ver in modules.items()]


def _make_device_config(**kwargs):
    """Create a minimal DeviceConfig for testing."""
    defaults = {
        "id": "test",
        "name": "Test Device",
        "type": "recamera_nodered",
        "nodered": NodeRedConfig(flow_file="flow.json"),
    }
    defaults.update(kwargs)
    return DeviceConfig(**defaults)


@pytest.fixture
def deployer():
    mod = _import_nodered_deployer()
    return mod.NodeRedDeployer()


@pytest.fixture
def progress_cb():
    return AsyncMock()


class TestEnsureModules:
    """Tests for NodeRedDeployer._ensure_modules"""

    @pytest.mark.asyncio
    async def test_skip_already_installed(self, deployer, progress_cb):
        """Module already installed with matching version -> skip."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(
                200,
                _make_nodes_response({"node-red-contrib-influxdb": "0.7.0"}),
            )
        )
        client.post = AsyncMock()

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        # POST /nodes should NOT be called
        client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_missing_module(self, deployer, progress_cb):
        """Module not installed -> install via POST /nodes."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"] == {
            "module": "node-red-contrib-influxdb",
            "version": "0.7.0",
        }

    @pytest.mark.asyncio
    async def test_update_version_mismatch(self, deployer, progress_cb):
        """Module installed with wrong version -> update via POST /nodes."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(
                200,
                _make_nodes_response({"node-red-contrib-influxdb": "0.6.1"}),
            )
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"]["version"] == "0.7.0"

    @pytest.mark.asyncio
    async def test_skip_when_no_version_required(self, deployer, progress_cb):
        """Module installed, no version specified -> skip regardless of version."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(
                200,
                _make_nodes_response({"node-red-contrib-influxdb": "0.5.0"}),
            )
        )
        client.post = AsyncMock()

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_without_version(self, deployer, progress_cb):
        """Module not installed, no version specified -> install without version."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"] == {"module": "node-red-contrib-influxdb"}

    @pytest.mark.asyncio
    async def test_install_failure_does_not_raise(self, deployer, progress_cb):
        """Install failure is logged as warning, does not abort."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(500, text="npm error"))

        # Should not raise
        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

    @pytest.mark.asyncio
    async def test_nodes_query_failure_returns_gracefully(self, deployer, progress_cb):
        """If GET /nodes fails, return without installing anything."""
        modules = [NodeRedModuleConfig(name="node-red-contrib-influxdb")]

        client = AsyncMock()
        client.get = AsyncMock(return_value=FakeResponse(500))
        client.post = AsyncMock()

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_modules(self, deployer, progress_cb):
        """Multiple modules: one installed, one missing."""
        modules = [
            NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0"),
            NodeRedModuleConfig(name="node-red-contrib-os", version="0.2.1"),
        ]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(
                200,
                _make_nodes_response({"node-red-contrib-influxdb": "0.7.0"}),
            )
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        await deployer._ensure_modules(
            client, "http://localhost:1880", modules, progress_cb
        )

        # Only the missing module should be installed
        client.post.assert_called_once()
        call_args = client.post.call_args
        assert call_args[1]["json"]["module"] == "node-red-contrib-os"


class TestEnsureModulesFallback:
    """Tests for three-level fallback in _ensure_modules."""

    @pytest.mark.asyncio
    async def test_level1_success_skips_proxy(self, deployer, progress_cb):
        """Level 1 (online) success → no proxy install attempted."""
        modules = [NodeRedModuleConfig(name="mod-a", version="1.0")]
        config = _make_device_config()
        connection = {"recamera_ip": "192.168.42.1", "ssh_password": "pw"}

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        with patch.object(deployer, "_proxy_install_module", new_callable=AsyncMock) as mock_proxy:
            mock_proxy.return_value = True
            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb, config, connection
            )
            mock_proxy.assert_not_called()

    @pytest.mark.asyncio
    async def test_level1_fail_triggers_proxy(self, deployer, progress_cb):
        """Level 1 fails → Level 2 proxy install attempted."""
        modules = [NodeRedModuleConfig(name="mod-a", version="1.0")]
        config = _make_device_config()
        connection = {"recamera_ip": "192.168.42.1", "ssh_password": "pw"}

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        # Level 1 fails
        client.post = AsyncMock(return_value=FakeResponse(500, text="no internet"))

        with patch.object(deployer, "_proxy_install_module", new_callable=AsyncMock) as mock_proxy, \
             patch.object(deployer, "_restart_nodered_service", new_callable=AsyncMock) as mock_restart, \
             patch.object(deployer, "_wait_for_nodered_ready", new_callable=AsyncMock) as mock_wait:
            mock_proxy.return_value = True
            mock_restart.return_value = True
            mock_wait.return_value = True

            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb, config, connection
            )

            mock_proxy.assert_called_once()
            # Proxy success → restart needed
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_level2_fail_triggers_offline(self, deployer, progress_cb):
        """Level 1+2 fail → Level 3 offline package attempted."""
        modules = [
            NodeRedModuleConfig(name="mod-a", version="1.0", offline_package="mod-a.tar.gz")
        ]
        config = _make_device_config()
        connection = {"recamera_ip": "192.168.42.1", "ssh_password": "pw"}

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(500, text="no internet"))

        with patch.object(deployer, "_proxy_install_module", new_callable=AsyncMock) as mock_proxy, \
             patch.object(deployer, "_install_from_offline_package", new_callable=AsyncMock) as mock_offline, \
             patch.object(deployer, "_restart_nodered_service", new_callable=AsyncMock) as mock_restart, \
             patch.object(deployer, "_wait_for_nodered_ready", new_callable=AsyncMock) as mock_wait:
            mock_proxy.return_value = False
            mock_offline.return_value = True
            mock_restart.return_value = True
            mock_wait.return_value = True

            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb, config, connection
            )

            mock_proxy.assert_called_once()
            mock_offline.assert_called_once()
            mock_restart.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_offline_package_skips_level3(self, deployer, progress_cb):
        """Level 1+2 fail, no offline_package → Level 3 skipped."""
        modules = [NodeRedModuleConfig(name="mod-a", version="1.0")]
        config = _make_device_config()
        connection = {"recamera_ip": "192.168.42.1", "ssh_password": "pw"}

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(500, text="no internet"))

        with patch.object(deployer, "_proxy_install_module", new_callable=AsyncMock) as mock_proxy, \
             patch.object(deployer, "_install_from_offline_package", new_callable=AsyncMock) as mock_offline:
            mock_proxy.return_value = False

            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb, config, connection
            )

            mock_proxy.assert_called_once()
            mock_offline.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_restart_when_only_online_installs(self, deployer, progress_cb):
        """Only Level 1 installs → no restart needed."""
        modules = [NodeRedModuleConfig(name="mod-a", version="1.0")]
        config = _make_device_config()
        connection = {"recamera_ip": "192.168.42.1", "ssh_password": "pw"}

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(200))

        with patch.object(deployer, "_restart_nodered_service", new_callable=AsyncMock) as mock_restart:
            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb, config, connection
            )
            mock_restart.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_config_skips_proxy_and_offline(self, deployer, progress_cb):
        """Without config/connection, Level 2+3 are skipped (backward compat)."""
        modules = [NodeRedModuleConfig(name="mod-a", version="1.0", offline_package="pkg.tar.gz")]

        client = AsyncMock()
        client.get = AsyncMock(
            return_value=FakeResponse(200, _make_nodes_response({}))
        )
        client.post = AsyncMock(return_value=FakeResponse(500, text="fail"))

        with patch.object(deployer, "_proxy_install_module", new_callable=AsyncMock) as mock_proxy, \
             patch.object(deployer, "_install_from_offline_package", new_callable=AsyncMock) as mock_offline:
            # Called without config/connection (old signature compat)
            await deployer._ensure_modules(
                client, "http://localhost:1880", modules, progress_cb
            )
            mock_proxy.assert_not_called()
            mock_offline.assert_not_called()


class TestNodeRedModuleConfig:
    """Tests for NodeRedModuleConfig model."""

    def test_with_version(self):
        mod = NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")
        assert mod.name == "node-red-contrib-influxdb"
        assert mod.version == "0.7.0"

    def test_without_version(self):
        mod = NodeRedModuleConfig(name="node-red-contrib-influxdb")
        assert mod.version is None

    def test_with_offline_package(self):
        mod = NodeRedModuleConfig(
            name="node-red-contrib-influxdb",
            version="0.7.0",
            offline_package="packages/influxdb.tar.gz",
        )
        assert mod.offline_package == "packages/influxdb.tar.gz"

    def test_without_offline_package(self):
        mod = NodeRedModuleConfig(name="node-red-contrib-influxdb")
        assert mod.offline_package is None

    def test_nodered_config_default_empty_modules(self):
        config = NodeRedConfig(flow_file="flow.json")
        assert config.modules == []

    def test_nodered_config_with_modules(self):
        config = NodeRedConfig(
            flow_file="flow.json",
            modules=[
                NodeRedModuleConfig(name="node-red-contrib-influxdb", version="0.7.0")
            ],
        )
        assert len(config.modules) == 1
        assert config.modules[0].name == "node-red-contrib-influxdb"
