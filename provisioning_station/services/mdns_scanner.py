"""
mDNS Scanner Service

Scans the local network for SSH-enabled devices using mDNS/Bonjour.
Uses zeroconf (pure Python mDNS client) which works on all platforms
without requiring Bonjour to be installed.
"""

import asyncio
import logging
import re
from typing import Optional

from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

logger = logging.getLogger(__name__)

# Known IoT device hostname patterns
KNOWN_DEVICE_PATTERNS = [
    re.compile(r"^raspberry.*", re.IGNORECASE),
    re.compile(r"^jetson.*", re.IGNORECASE),
    re.compile(r"^recomputer.*", re.IGNORECASE),
    re.compile(r"^recamera.*", re.IGNORECASE),
]

# Device type icons for frontend display
DEVICE_ICONS = {
    "raspberry": "raspberry",
    "jetson": "jetson",
    "recomputer": "recomputer",
    "recamera": "recamera",
}


def get_device_type(hostname: str) -> Optional[str]:
    """Get device type from hostname prefix."""
    hostname_lower = hostname.lower()
    for prefix, device_type in DEVICE_ICONS.items():
        if hostname_lower.startswith(prefix):
            return device_type
    return None


def is_known_device(hostname: str) -> bool:
    """Check if hostname matches a known IoT device pattern."""
    for pattern in KNOWN_DEVICE_PATTERNS:
        if pattern.match(hostname):
            return True
    return False


class MDNSScanner:
    """Scans the local network for SSH devices via mDNS."""

    def __init__(self):
        self._devices = {}
        self._zeroconf = None
        self._browser = None

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ) -> None:
        """Callback for service state changes."""
        if state_change == ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                # Extract hostname from service name (e.g., "raspberrypi._ssh._tcp.local.")
                hostname = name.replace(f".{service_type}", "").strip()

                # Get IP addresses
                addresses = []
                if info.addresses:
                    for addr in info.addresses:
                        try:
                            # Convert bytes to IP string
                            if len(addr) == 4:  # IPv4
                                ip = ".".join(str(b) for b in addr)
                                addresses.append(ip)
                        except Exception:
                            pass

                if addresses:
                    self._devices[hostname] = {
                        "hostname": hostname,
                        "ip": addresses[0],  # Primary IP
                        "port": info.port or 22,
                        "device_type": get_device_type(hostname),
                    }
                    logger.debug(f"Found SSH device: {hostname} at {addresses[0]}")

    async def scan_ssh_devices(
        self, timeout: float = 3.0, filter_known: bool = True
    ) -> list[dict]:
        """Scan for SSH devices on the local network.

        Args:
            timeout: Scan timeout in seconds (default: 3.0)
            filter_known: Only return devices matching known IoT patterns (default: True)

        Returns:
            List of device dictionaries with hostname, ip, port, device_type
        """
        self._devices = {}

        try:
            # Create zeroconf instance
            self._zeroconf = Zeroconf()

            # Browse for SSH services
            self._browser = ServiceBrowser(
                self._zeroconf,
                "_ssh._tcp.local.",
                handlers=[self._on_service_state_change],
            )

            # Wait for discovery
            await asyncio.sleep(timeout)

            # Get results
            devices = list(self._devices.values())

            # Filter to known devices if requested
            if filter_known:
                devices = [d for d in devices if is_known_device(d["hostname"])]

            # Sort by hostname
            devices.sort(key=lambda d: d["hostname"].lower())

            logger.info(f"mDNS scan found {len(devices)} devices")
            return devices

        except Exception as e:
            logger.error(f"mDNS scan failed: {e}")
            return []

        finally:
            # Cleanup
            if self._browser:
                self._browser.cancel()
                self._browser = None
            if self._zeroconf:
                self._zeroconf.close()
                self._zeroconf = None


async def resolve_mdns_hostname(hostname: str, timeout: float = 3.0) -> str | None:
    """Resolve a .local mDNS hostname to an IP address.

    This is useful for Windows where Docker containers cannot resolve .local addresses.
    If the hostname doesn't end with .local or resolution fails, returns None.

    Args:
        hostname: The hostname to resolve (e.g., 'recomputer.local')
        timeout: Resolution timeout in seconds

    Returns:
        IP address string if resolved, None otherwise
    """
    if not hostname or not hostname.lower().endswith(".local"):
        return None

    # Strip .local suffix for service lookup
    device_name = hostname[:-6]  # Remove '.local'

    try:
        zeroconf = Zeroconf()
        resolved_ip = None

        def on_service_state_change(
            zc: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
        ) -> None:
            nonlocal resolved_ip
            if state_change == ServiceStateChange.Added:
                info = zc.get_service_info(service_type, name)
                if info:
                    # Check if hostname matches
                    service_hostname = name.replace(f".{service_type}", "").strip()
                    if service_hostname.lower() == device_name.lower():
                        if info.addresses:
                            for addr in info.addresses:
                                if len(addr) == 4:  # IPv4
                                    resolved_ip = ".".join(str(b) for b in addr)
                                    return

        # Browse for SSH services to find the device
        browser = ServiceBrowser(
            zeroconf,
            "_ssh._tcp.local.",
            handlers=[on_service_state_change],
        )

        # Wait for resolution
        await asyncio.sleep(timeout)

        # Cleanup
        browser.cancel()
        zeroconf.close()

        if resolved_ip:
            logger.info(f"Resolved mDNS hostname {hostname} to {resolved_ip}")
        else:
            logger.warning(f"Could not resolve mDNS hostname: {hostname}")

        return resolved_ip

    except Exception as e:
        logger.error(f"mDNS resolution failed for {hostname}: {e}")
        return None


def is_mdns_hostname(hostname: str) -> bool:
    """Check if a hostname is an mDNS .local address."""
    return hostname and hostname.lower().endswith(".local")


# Singleton instance
mdns_scanner = MDNSScanner()
