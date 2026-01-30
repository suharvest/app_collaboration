"""
Port Configuration Tests

These tests verify that port configurations are consistent across the codebase.
This prevents the "port mismatch" regression where frontend and backend
use different default ports.

Files that must stay in sync:
- shared/constants.py: DEFAULT_PORT (source of truth)
- provisioning_station/config.py: Settings.port
- frontend/src/modules/api.js: getBackendPort() fallback values
"""

import re
from pathlib import Path

import pytest


class TestPortConfiguration:
    """Tests for port configuration consistency."""

    @pytest.fixture
    def project_root(self) -> Path:
        """Get the project root directory."""
        return Path(__file__).parent.parent.parent

    @pytest.fixture
    def expected_port(self) -> int:
        """Get the expected default port from shared constants."""
        from shared.constants import DEFAULT_PORT

        return DEFAULT_PORT

    def test_shared_constants_default_port(self, expected_port):
        """Verify DEFAULT_PORT is defined in shared constants."""
        assert expected_port == 3260, (
            f"DEFAULT_PORT should be 3260, got {expected_port}. "
            "If changing the default port, update all related files."
        )

    def test_backend_config_matches_constants(self, expected_port):
        """Verify provisioning_station/config.py uses the same default port."""
        from provisioning_station.config import Settings

        settings = Settings()
        assert settings.port == expected_port, (
            f"Backend config port ({settings.port}) does not match "
            f"shared constants ({expected_port})"
        )

    def test_frontend_api_js_fallback_matches(self, project_root, expected_port):
        """Verify frontend api.js has matching fallback port values."""
        api_js_path = project_root / "frontend" / "src" / "modules" / "api.js"

        assert api_js_path.exists(), f"api.js not found at {api_js_path}"

        content = api_js_path.read_text()

        # Find all hardcoded port numbers (look for patterns like :3260 or = 3260)
        port_patterns = [
            r"backendPort\s*=\s*(\d+)",  # backendPort = 3260
            r"return\s+(\d+)",  # return 3260
            r":\s*(\d+)/api",  # :3260/api
            r"\|\|\s*(\d+)",  # || 3260
        ]

        found_ports = set()
        for pattern in port_patterns:
            matches = re.findall(pattern, content)
            found_ports.update(int(m) for m in matches)

        # Filter to only include port-like values (not line numbers, etc.)
        port_values = [p for p in found_ports if 1000 <= p <= 65535]

        for port in port_values:
            assert port == expected_port, (
                f"Frontend api.js contains port {port} which does not match "
                f"expected port {expected_port}. Update api.js fallback values."
            )

    def test_api_js_has_fallback_logic(self, project_root):
        """Verify api.js has proper fallback port logic for Tauri mode."""
        api_js_path = project_root / "frontend" / "src" / "modules" / "api.js"
        content = api_js_path.read_text()

        # Should have __BACKEND_PORT__ check
        assert "__BACKEND_PORT__" in content, "api.js should check window.__BACKEND_PORT__"

        # Should have Tauri detection
        assert "__TAURI__" in content, "api.js should detect Tauri environment"

        # Should have fallback logic
        assert "fallback" in content.lower() or "3260" in content, (
            "api.js should have fallback port logic"
        )


class TestLanguageConfiguration:
    """Tests for language configuration consistency."""

    def test_supported_languages(self):
        """Verify supported languages match across codebase."""
        from shared.constants import SUPPORTED_LANGUAGES

        assert "en" in SUPPORTED_LANGUAGES, "English must be supported"
        assert "zh" in SUPPORTED_LANGUAGES, "Chinese must be supported"
        assert len(SUPPORTED_LANGUAGES) == 2, "Only en and zh should be supported"

    def test_default_language_is_supported(self):
        """Verify default language is one of the supported languages."""
        from shared.constants import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

        assert DEFAULT_LANGUAGE in SUPPORTED_LANGUAGES, (
            f"Default language '{DEFAULT_LANGUAGE}' is not in supported languages"
        )

    def test_backend_uses_supported_language(self):
        """Verify backend config uses a supported language."""
        from provisioning_station.config import settings
        from shared.constants import SUPPORTED_LANGUAGES

        assert settings.default_language in SUPPORTED_LANGUAGES, (
            f"Backend default_language '{settings.default_language}' "
            f"is not in supported languages"
        )


class TestTimeoutConfiguration:
    """Tests for timeout configuration consistency."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def test_request_timeout_defined(self):
        """Verify REQUEST_TIMEOUT_MS is defined."""
        from shared.constants import REQUEST_TIMEOUT_MS

        assert REQUEST_TIMEOUT_MS == 30000, "Request timeout should be 30000ms (30 seconds)"

    def test_frontend_timeout_matches(self, project_root):
        """Verify frontend REQUEST_TIMEOUT matches shared constants."""
        from shared.constants import REQUEST_TIMEOUT_MS

        api_js_path = project_root / "frontend" / "src" / "modules" / "api.js"
        content = api_js_path.read_text()

        # Look for REQUEST_TIMEOUT definition
        match = re.search(r"REQUEST_TIMEOUT\s*=\s*(\d+)", content)
        assert match is not None, "REQUEST_TIMEOUT not found in api.js"

        frontend_timeout = int(match.group(1))
        assert frontend_timeout == REQUEST_TIMEOUT_MS, (
            f"Frontend REQUEST_TIMEOUT ({frontend_timeout}) does not match "
            f"shared constants ({REQUEST_TIMEOUT_MS})"
        )


class TestDeviceTypeConfiguration:
    """Tests for device type consistency."""

    def test_device_types_defined(self):
        """Verify device types are defined in shared constants."""
        from shared.constants import DEVICE_TYPES

        expected_types = [
            "docker_local",
            "docker_deploy",
            "docker_remote",
            "esp32_usb",
            "himax_usb",
            "manual",
        ]

        for dtype in expected_types:
            assert dtype in DEVICE_TYPES, f"Missing device type: {dtype}"

    def test_backend_device_types_match(self):
        """Verify backend DeviceType enum matches shared constants."""
        from shared.constants import DEVICE_TYPES

        # Import backend DeviceType enum
        try:
            from provisioning_station.models.deployment import DeviceType

            backend_types = [dt.value for dt in DeviceType]

            for dtype in backend_types:
                assert dtype in DEVICE_TYPES, (
                    f"Backend DeviceType '{dtype}' not in shared constants"
                )
        except ImportError:
            pytest.skip("DeviceType enum not available")


class TestWebSocketConfiguration:
    """Tests for WebSocket message type consistency."""

    @pytest.fixture
    def project_root(self) -> Path:
        return Path(__file__).parent.parent.parent

    def test_ws_message_types_defined(self):
        """Verify WS message types are defined."""
        from shared.constants import WS_MESSAGE_TYPES

        required_types = ["log", "status", "progress", "ping", "pong"]
        for msg_type in required_types:
            assert msg_type in WS_MESSAGE_TYPES, f"Missing WS message type: {msg_type}"

    def test_frontend_handles_all_message_types(self, project_root):
        """Verify frontend LogsWebSocket handles all message types."""
        from shared.constants import WS_MESSAGE_TYPES

        api_js_path = project_root / "frontend" / "src" / "modules" / "api.js"
        content = api_js_path.read_text()

        # Find the onmessage handler section
        for msg_type in WS_MESSAGE_TYPES:
            # Check if the message type is handled (either in switch case or comment)
            pattern = rf"['\"]?{msg_type}['\"]?"
            assert re.search(pattern, content), (
                f"Frontend does not handle WS message type: {msg_type}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
