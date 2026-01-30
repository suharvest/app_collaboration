"""
Unit tests for mDNS Scanner Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from provisioning_station.services.mdns_scanner import (
    get_device_type,
    is_known_device,
    MDNSScanner,
    KNOWN_DEVICE_PATTERNS,
)


class TestGetDeviceType:
    """Tests for get_device_type function"""

    def test_raspberry_pi_variants(self):
        """Test Raspberry Pi hostname variants"""
        assert get_device_type("raspberrypi") == "raspberry"
        assert get_device_type("raspberry") == "raspberry"
        assert get_device_type("RaspberryPi") == "raspberry"
        assert get_device_type("RASPBERRY") == "raspberry"
        assert get_device_type("raspberrypi4") == "raspberry"
        assert get_device_type("raspberry-kitchen") == "raspberry"

    def test_jetson_variants(self):
        """Test NVIDIA Jetson hostname variants"""
        assert get_device_type("jetson") == "jetson"
        assert get_device_type("jetson-nano") == "jetson"
        assert get_device_type("Jetson-Orin") == "jetson"
        assert get_device_type("JETSON_AGX") == "jetson"
        assert get_device_type("jetson2") == "jetson"

    def test_recomputer_variants(self):
        """Test reComputer hostname variants"""
        assert get_device_type("recomputer") == "recomputer"
        assert get_device_type("reComputer") == "recomputer"
        assert get_device_type("RECOMPUTER") == "recomputer"
        assert get_device_type("recomputer-r1100") == "recomputer"
        assert get_device_type("recomputer_j4012") == "recomputer"

    def test_recamera_variants(self):
        """Test reCamera hostname variants"""
        assert get_device_type("recamera") == "recamera"
        assert get_device_type("reCamera") == "recamera"
        assert get_device_type("RECAMERA") == "recamera"
        assert get_device_type("recamera-001") == "recamera"

    def test_unknown_devices(self):
        """Test unknown device hostnames return None"""
        assert get_device_type("ubuntu-server") is None
        assert get_device_type("macbook-pro") is None
        assert get_device_type("my-desktop") is None
        assert get_device_type("localhost") is None
        assert get_device_type("nas") is None


class TestIsKnownDevice:
    """Tests for is_known_device function"""

    def test_known_devices_match(self):
        """Test known device patterns are matched"""
        assert is_known_device("raspberrypi") is True
        assert is_known_device("raspberry4") is True
        assert is_known_device("RASPBERRYPI") is True
        assert is_known_device("jetson-nano") is True
        assert is_known_device("Jetson") is True
        assert is_known_device("recomputer") is True
        assert is_known_device("reComputer-R1100") is True
        assert is_known_device("recamera") is True
        assert is_known_device("reCamera-001") is True

    def test_unknown_devices_not_matched(self):
        """Test unknown devices are not matched"""
        assert is_known_device("ubuntu") is False
        assert is_known_device("server01") is False
        assert is_known_device("my-macbook") is False
        assert is_known_device("linux-workstation") is False
        assert is_known_device("esp32-device") is False  # ESP32 is not in the list

    def test_partial_matches_not_accepted(self):
        """Test that partial matches at the end don't work"""
        assert is_known_device("my-raspberry") is False
        assert is_known_device("old-jetson") is False
        assert is_known_device("test-recomputer") is False
        assert is_known_device("backup-recamera") is False

    def test_empty_and_edge_cases(self):
        """Test empty and edge case inputs"""
        assert is_known_device("") is False
        assert is_known_device(" ") is False
        assert is_known_device("r") is False
        assert is_known_device("re") is False


class TestKnownDevicePatterns:
    """Tests for KNOWN_DEVICE_PATTERNS constant"""

    def test_patterns_exist(self):
        """Test that all expected patterns exist"""
        pattern_strings = [p.pattern for p in KNOWN_DEVICE_PATTERNS]
        assert any("raspberry" in p for p in pattern_strings)
        assert any("jetson" in p for p in pattern_strings)
        assert any("recomputer" in p for p in pattern_strings)
        assert any("recamera" in p for p in pattern_strings)

    def test_patterns_are_case_insensitive(self):
        """Test that patterns have IGNORECASE flag"""
        for pattern in KNOWN_DEVICE_PATTERNS:
            # All patterns should match regardless of case
            test_name = pattern.pattern.replace("^", "").replace(".*", "test")
            assert pattern.match(test_name)
            assert pattern.match(test_name.upper())
            assert pattern.match(test_name.lower())


class TestMDNSScanner:
    """Tests for MDNSScanner class"""

    def test_scanner_initialization(self):
        """Test scanner initializes with empty state"""
        scanner = MDNSScanner()
        assert scanner._devices == {}
        assert scanner._zeroconf is None
        assert scanner._browser is None

    @pytest.mark.asyncio
    async def test_scan_returns_list(self):
        """Test scan_ssh_devices returns a list"""
        scanner = MDNSScanner()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            with patch('provisioning_station.services.mdns_scanner.ServiceBrowser') as mock_browser:
                mock_zc = MagicMock()
                mock_zeroconf.return_value = mock_zc

                result = await scanner.scan_ssh_devices(timeout=0.1)

                assert isinstance(result, list)
                mock_zc.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_with_filter_known_true(self):
        """Test scan filters to known devices only"""
        scanner = MDNSScanner()

        def populate_devices(*args, **kwargs):
            # Simulate discovered devices after scanner starts
            scanner._devices = {
                "raspberrypi": {"hostname": "raspberrypi", "ip": "192.168.1.100", "port": 22, "device_type": "raspberry"},
                "ubuntu-server": {"hostname": "ubuntu-server", "ip": "192.168.1.101", "port": 22, "device_type": None},
                "jetson-nano": {"hostname": "jetson-nano", "ip": "192.168.1.102", "port": 22, "device_type": "jetson"},
            }
            return MagicMock()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            with patch('provisioning_station.services.mdns_scanner.ServiceBrowser', side_effect=populate_devices):
                mock_zc = MagicMock()
                mock_zeroconf.return_value = mock_zc

                result = await scanner.scan_ssh_devices(timeout=0.1, filter_known=True)

                # Only known devices should be returned
                hostnames = [d["hostname"] for d in result]
                assert "raspberrypi" in hostnames
                assert "jetson-nano" in hostnames
                assert "ubuntu-server" not in hostnames
                assert len(result) == 2

    @pytest.mark.asyncio
    async def test_scan_with_filter_known_false(self):
        """Test scan returns all devices when filter is off"""
        scanner = MDNSScanner()

        def populate_devices(*args, **kwargs):
            scanner._devices = {
                "raspberrypi": {"hostname": "raspberrypi", "ip": "192.168.1.100", "port": 22, "device_type": "raspberry"},
                "ubuntu-server": {"hostname": "ubuntu-server", "ip": "192.168.1.101", "port": 22, "device_type": None},
            }
            return MagicMock()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            with patch('provisioning_station.services.mdns_scanner.ServiceBrowser', side_effect=populate_devices):
                mock_zc = MagicMock()
                mock_zeroconf.return_value = mock_zc

                result = await scanner.scan_ssh_devices(timeout=0.1, filter_known=False)

                assert len(result) == 2
                hostnames = [d["hostname"] for d in result]
                assert "raspberrypi" in hostnames
                assert "ubuntu-server" in hostnames

    @pytest.mark.asyncio
    async def test_scan_results_sorted_by_hostname(self):
        """Test scan results are sorted alphabetically by hostname"""
        scanner = MDNSScanner()

        def populate_devices(*args, **kwargs):
            scanner._devices = {
                "zebra": {"hostname": "zebra", "ip": "192.168.1.3", "port": 22, "device_type": None},
                "apple": {"hostname": "apple", "ip": "192.168.1.1", "port": 22, "device_type": None},
                "banana": {"hostname": "banana", "ip": "192.168.1.2", "port": 22, "device_type": None},
            }
            return MagicMock()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            with patch('provisioning_station.services.mdns_scanner.ServiceBrowser', side_effect=populate_devices):
                mock_zc = MagicMock()
                mock_zeroconf.return_value = mock_zc

                result = await scanner.scan_ssh_devices(timeout=0.1, filter_known=False)

                hostnames = [d["hostname"] for d in result]
                assert hostnames == ["apple", "banana", "zebra"]

    @pytest.mark.asyncio
    async def test_scan_handles_exception(self):
        """Test scan handles exceptions gracefully"""
        scanner = MDNSScanner()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            mock_zeroconf.side_effect = Exception("Network error")

            result = await scanner.scan_ssh_devices(timeout=0.1)

            assert result == []

    @pytest.mark.asyncio
    async def test_scan_cleanup_on_success(self):
        """Test resources are cleaned up after successful scan"""
        scanner = MDNSScanner()

        with patch('provisioning_station.services.mdns_scanner.Zeroconf') as mock_zeroconf:
            with patch('provisioning_station.services.mdns_scanner.ServiceBrowser') as mock_browser:
                mock_zc = MagicMock()
                mock_zeroconf.return_value = mock_zc

                mock_br = MagicMock()
                mock_browser.return_value = mock_br

                await scanner.scan_ssh_devices(timeout=0.1)

                mock_br.cancel.assert_called_once()
                mock_zc.close.assert_called_once()
                assert scanner._browser is None
                assert scanner._zeroconf is None

    def test_service_state_change_handler_ipv4(self):
        """Test service state change handler extracts IPv4 correctly"""
        from zeroconf import ServiceStateChange

        scanner = MDNSScanner()
        mock_zeroconf = MagicMock()

        # Mock service info with IPv4 address
        mock_info = MagicMock()
        mock_info.addresses = [bytes([192, 168, 1, 100])]  # 192.168.1.100
        mock_info.port = 22
        mock_zeroconf.get_service_info.return_value = mock_info

        scanner._on_service_state_change(
            mock_zeroconf,
            "_ssh._tcp.local.",
            "raspberrypi._ssh._tcp.local.",
            ServiceStateChange.Added,
        )

        assert "raspberrypi" in scanner._devices
        assert scanner._devices["raspberrypi"]["ip"] == "192.168.1.100"
        assert scanner._devices["raspberrypi"]["port"] == 22
        assert scanner._devices["raspberrypi"]["device_type"] == "raspberry"

    def test_service_state_change_handler_no_addresses(self):
        """Test handler ignores services without addresses"""
        from zeroconf import ServiceStateChange

        scanner = MDNSScanner()
        mock_zeroconf = MagicMock()

        mock_info = MagicMock()
        mock_info.addresses = []
        mock_info.port = 22
        mock_zeroconf.get_service_info.return_value = mock_info

        scanner._on_service_state_change(
            mock_zeroconf,
            "_ssh._tcp.local.",
            "test._ssh._tcp.local.",
            ServiceStateChange.Added,
        )

        assert "test" not in scanner._devices

    def test_service_state_change_handler_removed_ignored(self):
        """Test handler ignores removed services"""
        from zeroconf import ServiceStateChange

        scanner = MDNSScanner()
        mock_zeroconf = MagicMock()

        scanner._on_service_state_change(
            mock_zeroconf,
            "_ssh._tcp.local.",
            "test._ssh._tcp.local.",
            ServiceStateChange.Removed,
        )

        # get_service_info should not be called for removed services
        mock_zeroconf.get_service_info.assert_not_called()


class TestMDNSScannerDeviceDict:
    """Tests for device dictionary structure"""

    def test_device_dict_has_required_fields(self):
        """Test device dictionary has all required fields"""
        from zeroconf import ServiceStateChange

        scanner = MDNSScanner()
        mock_zeroconf = MagicMock()

        mock_info = MagicMock()
        mock_info.addresses = [bytes([10, 0, 0, 5])]
        mock_info.port = 2222
        mock_zeroconf.get_service_info.return_value = mock_info

        scanner._on_service_state_change(
            mock_zeroconf,
            "_ssh._tcp.local.",
            "recomputer-r1100._ssh._tcp.local.",
            ServiceStateChange.Added,
        )

        device = scanner._devices["recomputer-r1100"]
        assert "hostname" in device
        assert "ip" in device
        assert "port" in device
        assert "device_type" in device

        assert device["hostname"] == "recomputer-r1100"
        assert device["ip"] == "10.0.0.5"
        assert device["port"] == 2222
        assert device["device_type"] == "recomputer"

    def test_device_dict_unknown_device_type(self):
        """Test unknown device type is None"""
        from zeroconf import ServiceStateChange

        scanner = MDNSScanner()
        mock_zeroconf = MagicMock()

        mock_info = MagicMock()
        mock_info.addresses = [bytes([192, 168, 0, 1])]
        mock_info.port = 22
        mock_zeroconf.get_service_info.return_value = mock_info

        scanner._on_service_state_change(
            mock_zeroconf,
            "_ssh._tcp.local.",
            "my-server._ssh._tcp.local.",
            ServiceStateChange.Added,
        )

        device = scanner._devices["my-server"]
        assert device["device_type"] is None
