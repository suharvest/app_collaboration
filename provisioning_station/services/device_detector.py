"""
Device detection service
"""

import asyncio
import glob as glob_module
import logging
import sys
from typing import Any, Dict, List, Optional

from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class DeviceDetector:
    """Hardware device detection service"""

    async def detect_device(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect a device based on its configuration"""
        if config.type == "esp32_usb":
            return await self._detect_esp32_usb(config)
        elif config.type == "himax_usb":
            return await self._detect_himax_usb(config)
        elif config.type == "docker_local":
            return await self._detect_docker_local(config)
        elif config.type == "docker_remote":
            return await self._detect_docker_remote(config)
        elif config.type == "ssh_deb":
            return await self._detect_ssh_device(config)
        elif config.type == "script":
            return await self._detect_script_environment(config)
        elif config.type == "manual":
            return await self._detect_manual(config)
        else:
            return {
                "status": "error",
                "details": {"error": f"Unknown device type: {config.type}"},
            }

    async def _detect_esp32_usb(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect ESP32 device via USB serial"""
        try:
            import serial.tools.list_ports

            ports = list(serial.tools.list_ports.comports())
            detection = config.detection

            # Match by VID/PID if specified
            if detection.usb_vendor_id and detection.usb_product_id:
                matched_ports = []
                for port in ports:
                    if port.vid and port.pid:
                        vid = f"0x{port.vid:04x}"
                        pid = f"0x{port.pid:04x}"

                        if (
                            vid.lower() == detection.usb_vendor_id.lower()
                            and pid.lower() == detection.usb_product_id.lower()
                        ):
                            matched_ports.append((port, vid, pid))

                if matched_ports:
                    # For dual-serial USB devices (like SenseCAP Watcher with CH342):
                    # - Multiple ports share the same serial_number but differ in interface
                    # - macOS: usbmodem*51 = Himax JTAG, usbmodem*53 = ESP32 UART
                    # - Windows: SERIAL-A = Himax, SERIAL-B = ESP32
                    # - Linux: ttyACM0 (interface 0) = Himax, ttyACM1 (interface 2) = ESP32
                    # Strategy: prefer *53/SERIAL-B/higher interface for ESP32

                    # Group by serial number to detect dual-serial devices
                    by_serial = {}
                    for port, vid, pid in matched_ports:
                        sn = port.serial_number or "unknown"
                        if sn not in by_serial:
                            by_serial[sn] = []
                        by_serial[sn].append((port, vid, pid))

                    # Helper function to determine ESP32 priority
                    # Positive = likely ESP32, Negative = likely Himax, 0 = unknown
                    def get_esp32_priority(item):
                        port = item[0]
                        desc = (port.description or "").upper()
                        device = port.device.lower()

                        # Windows: prefer SERIAL-B for ESP32
                        if "SERIAL-B" in desc:
                            return 100
                        if "SERIAL-A" in desc:
                            return -100  # This is Himax, not ESP32

                        # macOS: *53 = ESP32 UART, *51 = Himax JTAG
                        # Both wchusbserial and usbmodem follow this pattern
                        if device.endswith("53") or device.endswith("653"):
                            return 100  # ESP32 UART interface
                        if device.endswith("51") or device.endswith("651"):
                            return -100  # This is Himax JTAG

                        # Fallback: check last digit
                        if device[-1] == "3":
                            return 90
                        if device[-1] == "1":
                            return -90

                        # Linux: parse interface from location (e.g., "1-1:1.2" -> interface 2)
                        # ttyACM0 (interface 0) = Himax, ttyACM1 (interface 2) = ESP32
                        if port.location:
                            # Location format: bus-port:config.interface
                            try:
                                iface = int(port.location.split('.')[-1])
                                return iface  # Higher interface = ESP32
                            except (ValueError, IndexError):
                                pass

                        # Fallback: use interface number directly
                        if port.interface is not None:
                            try:
                                return int(port.interface)
                            except (ValueError, TypeError):
                                pass

                        # Last fallback: use port name suffix
                        if device and device[-1].isdigit():
                            return int(device[-1])
                        return 0

                    # Select best port from each serial number group
                    # IMPORTANT: Always filter by priority, even for single-port groups
                    best_port = None
                    best_priority = -999
                    for sn, port_list in by_serial.items():
                        for port_item in port_list:
                            priority = get_esp32_priority(port_item)
                            logger.debug(f"ESP32 port candidate: {port_item[0].device}, priority={priority}")

                            # Only consider ports with positive priority (likely ESP32)
                            if priority > 0 and priority > best_priority:
                                best_priority = priority
                                best_port = port_item

                        if len(port_list) > 1:
                            logger.info(
                                f"Dual-serial device detected (serial={sn}), "
                                f"ports: {[p[0].device for p in port_list]}"
                            )

                    if best_port:
                        logger.info(f"Selected ESP32 port: {best_port[0].device} (priority={best_priority})")
                        port, vid, pid = best_port
                        return {
                            "status": "detected",
                            "connection_info": {"port": port.device},
                            "details": {
                                "port": port.device,
                                "description": port.description,
                                "manufacturer": port.manufacturer,
                                "vid": vid,
                                "pid": pid,
                                "serial_number": port.serial_number,
                                "all_matching_ports": [p[0].device for p in matched_ports],
                            },
                        }

            # Fallback: check common port patterns (cross-platform)
            fallback_ports = detection.fallback_ports or self._get_platform_port_patterns()

            # On Windows, glob doesn't work for COM ports - use pyserial directly
            if sys.platform == "win32":
                for port_path in self._get_windows_com_ports():
                    try:
                        import serial
                        ser = serial.Serial(port_path, 115200, timeout=1)
                        ser.close()
                        return {
                            "status": "detected",
                            "connection_info": {"port": port_path},
                            "details": {"port": port_path, "matched_pattern": "COM*"},
                        }
                    except Exception:
                        continue
            else:
                # Unix-like: use glob patterns
                for pattern in fallback_ports:
                    for port_path in glob_module.glob(pattern):
                        # Verify it's accessible
                        try:
                            import serial
                            ser = serial.Serial(port_path, 115200, timeout=1)
                            ser.close()
                            return {
                                "status": "detected",
                                "connection_info": {"port": port_path},
                                "details": {"port": port_path, "matched_pattern": pattern},
                            }
                        except Exception:
                            continue

            return {
                "status": "not_detected",
                "details": {
                    "message": "No matching USB device found",
                    "available_ports": [p.device for p in ports],
                    "searched_patterns": fallback_ports,
                },
            }

        except ImportError:
            return {
                "status": "error",
                "details": {"error": "pyserial not installed"},
            }
        except Exception as e:
            logger.error(f"ESP32 detection error: {e}")
            return {
                "status": "error",
                "details": {"error": str(e)},
            }

    async def _detect_himax_usb(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect Himax WE2 device via USB serial

        For SenseCAP Watcher, the device exposes multiple ports with same VID/PID:
        - usbmodemXXXXX1: Himax WE2 (what we want)
        - usbmodemXXXXX3: Another interface
        - wchusbserialXXX: ESP32 (NOT what we want)

        Strategy: prefer usbmodem ports ending with '1'
        """
        try:
            import serial.tools.list_ports

            ports = list(serial.tools.list_ports.comports())
            detection = config.detection

            # Match by VID/PID if specified
            if detection.usb_vendor_id and detection.usb_product_id:
                matched_ports = []
                for port in ports:
                    if port.vid and port.pid:
                        vid = f"0x{port.vid:04x}"
                        pid = f"0x{port.pid:04x}"

                        if (
                            vid.lower() == detection.usb_vendor_id.lower()
                            and pid.lower() == detection.usb_product_id.lower()
                        ):
                            # Include all matching ports, filter by interface number later
                            matched_ports.append((port, vid, pid))

                if matched_ports:
                    # For Himax on SenseCAP Watcher:
                    # - macOS: *51/*651 (末尾1) = Himax, *53/*653 (末尾3) = ESP32
                    # - Windows: SERIAL-A = Himax, SERIAL-B = ESP32
                    # - Linux: ttyACM0 (interface 0) = Himax, ttyACM1 (interface 2) = ESP32
                    # Port type (wchusbserial/usbmodem) doesn't matter, only interface number

                    def get_himax_priority(item):
                        port = item[0]
                        desc = (port.description or "").upper()
                        device = port.device.lower()

                        # Windows: prefer SERIAL-A for Himax
                        if "SERIAL-A" in desc:
                            return -100  # Lower is better (sorted first)
                        if "SERIAL-B" in desc:
                            return 100  # This is ESP32, not Himax

                        # macOS: *51/*651 (末尾1) = Himax, *53/*653 (末尾3) = ESP32
                        # Check last digit - '1' means Himax, '3' means ESP32
                        if device[-1] == "1":
                            return -100  # Himax - selected first
                        if device[-1] == "3":
                            return 100  # ESP32 - excluded

                        # Linux: parse interface from location, prefer lower interface for Himax
                        if port.location:
                            try:
                                iface = int(port.location.split('.')[-1])
                                return iface  # Lower interface (0) sorted first
                            except (ValueError, IndexError):
                                pass

                        if device and device[-1].isdigit():
                            return int(device[-1])
                        return 99

                    matched_ports.sort(key=get_himax_priority)
                    logger.info(
                        f"Himax ports found, selecting {matched_ports[0][0].device} "
                        f"from {[p[0].device for p in matched_ports]}"
                    )

                    port, vid, pid = matched_ports[0]
                    return {
                        "status": "detected",
                        "connection_info": {"port": port.device},
                        "details": {
                            "port": port.device,
                            "description": port.description,
                            "manufacturer": port.manufacturer,
                            "vid": vid,
                            "pid": pid,
                            "serial_number": port.serial_number,
                            "all_matching_ports": [p[0].device for p in matched_ports],
                        },
                    }

            # Fallback: check common usbmodem patterns
            if sys.platform == "win32":
                fallback_ports = detection.fallback_ports or ["COM*"]
            else:
                fallback_ports = detection.fallback_ports or [
                    "/dev/cu.usbmodem*",
                    "/dev/tty.usbmodem*",
                    "/dev/ttyACM*",
                ]

            # On Windows, use pyserial to enumerate COM ports
            if sys.platform == "win32":
                for port_path in self._get_windows_com_ports():
                    try:
                        import serial
                        ser = serial.Serial(port_path, 115200, timeout=1)
                        ser.close()
                        return {
                            "status": "detected",
                            "connection_info": {"port": port_path},
                            "details": {"port": port_path, "matched_pattern": "COM*"},
                        }
                    except Exception:
                        continue
            else:
                for pattern in fallback_ports:
                    for port_path in glob_module.glob(pattern):
                        try:
                            import serial
                            ser = serial.Serial(port_path, 115200, timeout=1)
                            ser.close()
                            return {
                                "status": "detected",
                                "connection_info": {"port": port_path},
                                "details": {"port": port_path, "matched_pattern": pattern},
                            }
                        except Exception:
                            continue

            return {
                "status": "not_detected",
                "details": {
                    "message": "No Himax device found",
                    "available_ports": [p.device for p in ports],
                    "searched_patterns": fallback_ports,
                },
            }

        except ImportError:
            return {
                "status": "error",
                "details": {"error": "pyserial not installed"},
            }
        except Exception as e:
            logger.error(f"Himax detection error: {e}")
            return {
                "status": "error",
                "details": {"error": str(e)},
            }

    def _get_platform_port_patterns(self) -> List[str]:
        """Get platform-specific serial port patterns

        Note: On Windows, glob patterns like 'COM*' don't work directly.
        We return patterns for documentation but the actual detection
        uses pyserial's list_ports which works cross-platform.
        """
        if sys.platform == "win32":
            # Windows COM port patterns - used for documentation/filtering
            # glob.glob won't match these; we rely on pyserial list_ports
            # Common USB-Serial adapters create ports like COM3, COM4, etc.
            return [
                "COM*",  # Generic COM ports
            ]
        elif sys.platform == "darwin":
            return [
                "/dev/tty.usbserial-*",
                "/dev/cu.usbserial-*",
                "/dev/tty.wchusbserial*",
                "/dev/cu.wchusbserial*",
                "/dev/tty.SLAB_USBtoUART*",
                "/dev/cu.SLAB_USBtoUART*",
            ]
        else:  # Linux
            return [
                "/dev/ttyUSB*",
                "/dev/ttyACM*",
            ]

    def _get_windows_com_ports(self) -> List[str]:
        """Get available COM ports on Windows using pyserial"""
        try:
            import serial.tools.list_ports
            ports = []
            for port in serial.tools.list_ports.comports():
                if port.device.upper().startswith("COM"):
                    ports.append(port.device)
            return sorted(ports, key=lambda x: int(x[3:]) if x[3:].isdigit() else 999)
        except Exception:
            return []

    async def _detect_docker_local(self, config: DeviceConfig) -> Dict[str, Any]:
        """Check local Docker availability"""
        try:
            import docker

            client = docker.from_env()
            info = client.info()

            # Check requirements
            missing = []
            for req in config.detection.requirements:
                if req == "docker_installed":
                    pass  # If we got here, Docker is installed
                elif req == "docker_running":
                    pass  # If we got here, Docker is running
                elif req == "docker_compose_installed":
                    # Check docker compose
                    try:
                        result = await asyncio.create_subprocess_exec(
                            "docker", "compose", "version",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        await result.communicate()
                        if result.returncode != 0:
                            missing.append("docker_compose")
                    except Exception:
                        missing.append("docker_compose")

            if missing:
                return {
                    "status": "error",
                    "details": {"missing_requirements": missing},
                }

            return {
                "status": "detected",
                "connection_info": {"local": True},
                "details": {
                    "docker_version": info.get("ServerVersion"),
                    "os": info.get("OperatingSystem"),
                    "arch": info.get("Architecture"),
                    "containers_running": info.get("ContainersRunning", 0),
                },
            }

        except ImportError:
            return {
                "status": "error",
                "details": {"error": "docker package not installed"},
            }
        except Exception as e:
            logger.error(f"Docker detection error: {e}")
            return {
                "status": "error",
                "details": {"error": str(e)},
            }

    async def _detect_docker_remote(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect remote Docker deployment target"""
        # For remote Docker, always return manual_required
        # User needs to provide IP and SSH credentials
        return {
            "status": "manual_required",
            "connection_info": None,
            "details": {
                "message": "Please enter remote host IP and SSH credentials",
                "default_user": config.ssh.default_user if config.ssh else "root",
                "default_port": config.ssh.port if config.ssh else 22,
            },
        }

    async def _detect_ssh_device(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect SSH-accessible devices"""
        # For SSH devices, return as "manual_required" by default
        # User needs to provide IP and credentials
        return {
            "status": "manual_required",
            "connection_info": None,
            "details": {
                "message": "Please enter device IP address and credentials",
                "default_user": config.ssh.default_user if config.ssh else "root",
                "default_port": config.ssh.port if config.ssh else 22,
            },
        }

    async def _detect_script_environment(self, config: DeviceConfig) -> Dict[str, Any]:
        """Check local script execution environment"""
        detection = config.detection
        missing = []

        for req in detection.requirements:
            if req == "python_installed":
                if not await self._check_command_exists("python3", ["--version"]):
                    if not await self._check_command_exists("python", ["--version"]):
                        missing.append("python")
            elif req == "uv_installed":
                if not await self._check_command_exists("uv", ["--version"]):
                    missing.append("uv")
            elif req == "node_installed":
                if not await self._check_command_exists("node", ["--version"]):
                    missing.append("node")
            elif req == "npm_installed":
                if not await self._check_command_exists("npm", ["--version"]):
                    missing.append("npm")

        if missing:
            return {
                "status": "error",
                "connection_info": None,
                "details": {
                    "missing_requirements": missing,
                    "message": f"Missing requirements: {', '.join(missing)}",
                },
            }

        # For script type, always return manual_required since user inputs are needed
        if detection.method == "manual" or detection.manual_entry:
            return {
                "status": "manual_required",
                "connection_info": {"local": True},
                "details": {
                    "message": "User inputs required for deployment",
                    "requirements_met": True,
                },
            }

        return {
            "status": "detected",
            "connection_info": {"local": True},
            "details": {
                "requirements_met": True,
                "platform": await self._get_platform_info(),
            },
        }

    async def _detect_manual(self, config: DeviceConfig) -> Dict[str, Any]:
        """Handle manual deployment type (user performs steps manually)"""
        return {
            "status": "manual",
            "connection_info": {"manual": True},
            "details": {
                "message": "Manual steps - no automated deployment",
            },
        }

    async def _check_command_exists(self, cmd: str, args: List[str]) -> bool:
        """Check if a command is available in the system"""
        try:
            process = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False

    async def _get_platform_info(self) -> Dict[str, str]:
        """Get platform information"""
        import platform
        import sys
        return {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": sys.version.split()[0],
        }

    async def list_serial_ports(self) -> List[Dict[str, Any]]:
        """List all available serial ports"""
        try:
            import serial.tools.list_ports

            logger.info(f"Listing serial ports on platform: {sys.platform}")

            # On Windows, list_ports.comports() should work directly
            # On some systems, we may need to iterate manually
            raw_ports = list(serial.tools.list_ports.comports())
            logger.info(f"Found {len(raw_ports)} raw ports")

            ports = []
            for port in raw_ports:
                logger.debug(f"Port: {port.device}, desc: {port.description}, vid: {port.vid}, pid: {port.pid}")
                ports.append({
                    "device": port.device,
                    "description": port.description or "",
                    "manufacturer": port.manufacturer or "",
                    "vid": f"0x{port.vid:04x}" if port.vid else None,
                    "pid": f"0x{port.pid:04x}" if port.pid else None,
                })

            # On Windows, if no ports found, try alternative method
            if not ports and sys.platform == "win32":
                logger.info("No ports from comports(), trying Windows registry method")
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM")
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            logger.info(f"Registry port: {value}")
                            ports.append({
                                "device": value,
                                "description": name,
                                "manufacturer": "",
                                "vid": None,
                                "pid": None,
                            })
                            i += 1
                        except OSError:
                            break
                    winreg.CloseKey(key)
                except Exception as e:
                    logger.warning(f"Windows registry method failed: {e}")

            logger.info(f"Returning {len(ports)} ports")
            return ports

        except ImportError as e:
            logger.error(f"pyserial not installed: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to list serial ports: {e}", exc_info=True)
            return []

    async def test_serial_port(self, port: str) -> Dict[str, Any]:
        """Test if a serial port is accessible"""
        try:
            import serial

            ser = serial.Serial(port, 115200, timeout=1)
            ser.close()

            return {
                "status": "detected",
                "connection_info": {"port": port},
                "details": {"port": port},
            }

        except Exception as e:
            return {
                "status": "error",
                "details": {"error": str(e)},
            }

    async def test_ssh_connection(
        self,
        host: str,
        port: int = 22,
        username: str = "root",
        password: Optional[str] = None,
        key_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Test SSH connection to a device"""
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                if key_file:
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        key_filename=key_file,
                        timeout=10,
                    )
                else:
                    client.connect(
                        hostname=host,
                        port=port,
                        username=username,
                        password=password,
                        timeout=10,
                    )

                # Get device info
                stdin, stdout, stderr = client.exec_command("uname -a")
                uname = stdout.read().decode().strip()

                stdin, stdout, stderr = client.exec_command("cat /etc/os-release 2>/dev/null || echo 'Unknown'")
                os_info = stdout.read().decode().strip()

                client.close()

                return {
                    "status": "detected",
                    "connection_info": {
                        "host": host,
                        "port": port,
                        "username": username,
                    },
                    "details": {
                        "uname": uname,
                        "os_info": os_info[:200],  # Truncate
                    },
                }

            except paramiko.AuthenticationException:
                return {
                    "status": "error",
                    "details": {"error": "Authentication failed"},
                }
            except paramiko.SSHException as e:
                return {
                    "status": "error",
                    "details": {"error": f"SSH error: {str(e)}"},
                }
            finally:
                client.close()

        except ImportError:
            return {
                "status": "error",
                "details": {"error": "paramiko not installed"},
            }
        except Exception as e:
            logger.error(f"SSH connection test error: {e}")
            return {
                "status": "error",
                "details": {"error": str(e)},
            }


# Global instance
device_detector = DeviceDetector()
