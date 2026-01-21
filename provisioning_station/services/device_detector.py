"""
Device detection service
"""

import asyncio
import glob as glob_module
import logging
import sys
from typing import Dict, Any, List, Optional

from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class DeviceDetector:
    """Hardware device detection service"""

    async def detect_device(self, config: DeviceConfig) -> Dict[str, Any]:
        """Detect a device based on its configuration"""
        if config.type == "esp32_usb":
            return await self._detect_esp32_usb(config)
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
                for port in ports:
                    if port.vid and port.pid:
                        vid = f"0x{port.vid:04x}"
                        pid = f"0x{port.pid:04x}"

                        if (
                            vid.lower() == detection.usb_vendor_id.lower()
                            and pid.lower() == detection.usb_product_id.lower()
                        ):
                            return {
                                "status": "detected",
                                "connection_info": {"port": port.device},
                                "details": {
                                    "port": port.device,
                                    "description": port.description,
                                    "manufacturer": port.manufacturer,
                                    "vid": vid,
                                    "pid": pid,
                                },
                            }

            # Fallback: check common port patterns (cross-platform)
            fallback_ports = detection.fallback_ports or self._get_platform_port_patterns()

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

    def _get_platform_port_patterns(self) -> List[str]:
        """Get platform-specific serial port patterns"""
        if sys.platform == "win32":
            return ["COM*"]
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
        import sys
        import platform
        return {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": sys.version.split()[0],
        }

    async def list_serial_ports(self) -> List[Dict[str, Any]]:
        """List all available serial ports"""
        try:
            import serial.tools.list_ports

            ports = []
            for port in serial.tools.list_ports.comports():
                ports.append({
                    "device": port.device,
                    "description": port.description,
                    "manufacturer": port.manufacturer,
                    "vid": f"0x{port.vid:04x}" if port.vid else None,
                    "pid": f"0x{port.pid:04x}" if port.pid else None,
                })
            return ports

        except ImportError:
            return []
        except Exception as e:
            logger.error(f"Failed to list serial ports: {e}")
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
