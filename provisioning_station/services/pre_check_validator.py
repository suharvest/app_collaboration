"""
Pre-deployment check validation service
"""

import asyncio
import logging
import re
import shutil
import socket
from typing import List, Dict, Any, Optional

from pydantic import BaseModel

from ..models.device import PreCheck

logger = logging.getLogger(__name__)


class CheckResult(BaseModel):
    """Result of a pre-deployment check"""
    type: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class PreCheckValidator:
    """Validates pre-deployment requirements"""

    async def validate_all(self, checks: List[PreCheck]) -> List[CheckResult]:
        """Validate all pre-checks"""
        results = []
        for check in checks:
            result = await self._validate(check)
            results.append(result)
        return results

    async def _validate(self, check: PreCheck) -> CheckResult:
        """Validate a single pre-check"""
        try:
            check_method = getattr(self, f"_validate_{check.type}", None)
            if check_method:
                return await check_method(check)
            else:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message=f"Unknown check type: {check.type}",
                )
        except Exception as e:
            logger.error(f"Pre-check validation error for {check.type}: {e}")
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Check failed with error: {str(e)}",
            )

    async def _validate_docker_version(self, check: PreCheck) -> CheckResult:
        """Check Docker version"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message="Docker is not installed or not running",
                )

            # Parse version: Docker version 24.0.5, build ced0996
            version_str = stdout.decode().strip()
            match = re.search(r"Docker version (\d+\.\d+\.\d+)", version_str)
            if match:
                current_version = match.group(1)

                if check.min_version:
                    if self._compare_versions(current_version, check.min_version) < 0:
                        return CheckResult(
                            type=check.type,
                            passed=False,
                            message=f"Docker version {current_version} is below required {check.min_version}",
                            details={"current_version": current_version, "required_version": check.min_version},
                        )

                return CheckResult(
                    type=check.type,
                    passed=True,
                    message=f"Docker version {current_version}",
                    details={"version": current_version},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message="Docker is available",
                details={"raw_version": version_str},
            )

        except FileNotFoundError:
            return CheckResult(
                type=check.type,
                passed=False,
                message="Docker is not installed",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check Docker: {str(e)}",
            )

    async def _validate_docker_compose_version(self, check: PreCheck) -> CheckResult:
        """Check Docker Compose version"""
        try:
            process = await asyncio.create_subprocess_exec(
                "docker", "compose", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message="Docker Compose is not available",
                )

            # Parse version: Docker Compose version v2.20.2
            version_str = stdout.decode().strip()
            match = re.search(r"v?(\d+\.\d+\.\d+)", version_str)
            if match:
                current_version = match.group(1)

                if check.min_version:
                    if self._compare_versions(current_version, check.min_version) < 0:
                        return CheckResult(
                            type=check.type,
                            passed=False,
                            message=f"Docker Compose version {current_version} is below required {check.min_version}",
                            details={"current_version": current_version, "required_version": check.min_version},
                        )

                return CheckResult(
                    type=check.type,
                    passed=True,
                    message=f"Docker Compose version {current_version}",
                    details={"version": current_version},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message="Docker Compose is available",
                details={"raw_version": version_str},
            )

        except FileNotFoundError:
            return CheckResult(
                type=check.type,
                passed=False,
                message="Docker Compose is not installed",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check Docker Compose: {str(e)}",
            )

    async def _validate_port_available(self, check: PreCheck) -> CheckResult:
        """Check if ports are available"""
        unavailable_ports = []

        for port in check.ports:
            if not self._is_port_available(port):
                unavailable_ports.append(port)

        if unavailable_ports:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Ports {unavailable_ports} are already in use",
                details={"unavailable_ports": unavailable_ports, "required_ports": check.ports},
            )

        return CheckResult(
            type=check.type,
            passed=True,
            message=f"All required ports are available: {check.ports}",
            details={"available_ports": check.ports},
        )

    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind(("127.0.0.1", port))
                return True
        except socket.error:
            return False

    async def _validate_disk_space(self, check: PreCheck) -> CheckResult:
        """Check available disk space"""
        try:
            total, used, free = shutil.disk_usage("/")
            free_gb = free / (1024 ** 3)

            min_gb = check.min_gb or 0
            if free_gb < min_gb:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message=f"Insufficient disk space: {free_gb:.1f}GB available, {min_gb}GB required",
                    details={"free_gb": free_gb, "required_gb": min_gb},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message=f"Disk space: {free_gb:.1f}GB available",
                details={"free_gb": free_gb, "required_gb": min_gb},
            )

        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check disk space: {str(e)}",
            )

    async def _validate_esptool_version(self, check: PreCheck) -> CheckResult:
        """Check esptool version"""
        try:
            process = await asyncio.create_subprocess_exec(
                "esptool.py", "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                # Try with python -m esptool
                process = await asyncio.create_subprocess_exec(
                    "python", "-m", "esptool", "version",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await process.communicate()

            if process.returncode != 0:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message="esptool is not installed",
                )

            version_str = stdout.decode().strip()
            match = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_str)
            if match:
                current_version = match.group(1)

                if check.min_version:
                    if self._compare_versions(current_version, check.min_version) < 0:
                        return CheckResult(
                            type=check.type,
                            passed=False,
                            message=f"esptool version {current_version} is below required {check.min_version}",
                            details={"current_version": current_version, "required_version": check.min_version},
                        )

                return CheckResult(
                    type=check.type,
                    passed=True,
                    message=f"esptool version {current_version}",
                    details={"version": current_version},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message="esptool is available",
            )

        except FileNotFoundError:
            return CheckResult(
                type=check.type,
                passed=False,
                message="esptool is not installed",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check esptool: {str(e)}",
            )

    async def _validate_esptool_available(self, check: PreCheck) -> CheckResult:
        """Check if esptool is available (alias for esptool_version without version check)"""
        return await self._validate_esptool_version(check)

    async def _validate_serial_port_available(self, check: PreCheck) -> CheckResult:
        """Check if serial port is accessible

        Note: This is a soft check - the actual port validation happens during deployment
        when the user selects a port. This pre-check just verifies basic serial port
        access capability on the system.
        """
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())

            if not ports:
                return CheckResult(
                    type=check.type,
                    passed=True,  # Pass even with no ports - user might connect device later
                    message="No serial ports detected. Please connect your device.",
                    details={"port_count": 0},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message=f"Serial port access available ({len(ports)} ports found)",
                details={"port_count": len(ports), "ports": [p.device for p in ports]},
            )

        except ImportError:
            return CheckResult(
                type=check.type,
                passed=False,
                message="pyserial is not installed",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check serial ports: {str(e)}",
            )

    async def _validate_python_installed(self, check: PreCheck) -> CheckResult:
        """Check if Python is installed"""
        try:
            for python_cmd in ["python3", "python"]:
                try:
                    process = await asyncio.create_subprocess_exec(
                        python_cmd, "--version",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    stdout, _ = await process.communicate()

                    if process.returncode == 0:
                        version_str = stdout.decode().strip()
                        match = re.search(r"Python (\d+\.\d+\.\d+)", version_str)
                        version = match.group(1) if match else version_str

                        return CheckResult(
                            type=check.type,
                            passed=True,
                            message=f"Python {version}",
                            details={"version": version, "command": python_cmd},
                        )
                except FileNotFoundError:
                    continue

            return CheckResult(
                type=check.type,
                passed=False,
                message="Python is not installed",
            )

        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check Python: {str(e)}",
            )

    async def _validate_uv_installed(self, check: PreCheck) -> CheckResult:
        """Check if uv package manager is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "uv", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()

            if process.returncode != 0:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message="uv is not installed",
                )

            version_str = stdout.decode().strip()
            match = re.search(r"uv (\d+\.\d+\.\d+)", version_str)
            version = match.group(1) if match else version_str

            return CheckResult(
                type=check.type,
                passed=True,
                message=f"uv version {version}",
                details={"version": version},
            )

        except FileNotFoundError:
            return CheckResult(
                type=check.type,
                passed=False,
                message="uv is not installed",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check uv: {str(e)}",
            )

    async def _validate_memory_available(self, check: PreCheck) -> CheckResult:
        """Check available memory"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 ** 2)

            min_mb = check.min_mb or 0
            if available_mb < min_mb:
                return CheckResult(
                    type=check.type,
                    passed=False,
                    message=f"Insufficient memory: {available_mb:.0f}MB available, {min_mb}MB required",
                    details={"available_mb": available_mb, "required_mb": min_mb},
                )

            return CheckResult(
                type=check.type,
                passed=True,
                message=f"Memory: {available_mb:.0f}MB available",
                details={"available_mb": available_mb, "required_mb": min_mb},
            )

        except ImportError:
            # psutil not available, skip check
            return CheckResult(
                type=check.type,
                passed=True,
                message="Memory check skipped (psutil not available)",
            )
        except Exception as e:
            return CheckResult(
                type=check.type,
                passed=False,
                message=f"Failed to check memory: {str(e)}",
            )

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        def normalize(v):
            return [int(x) for x in re.sub(r"[^\d.]", "", v).split(".")]

        v1_parts = normalize(v1)
        v2_parts = normalize(v2)

        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))

        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1

        return 0


# Global instance
pre_check_validator = PreCheckValidator()
