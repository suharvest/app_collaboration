"""
Device Restore Manager Service

Handles restoring devices to factory state:
- SenseCAP Watcher: USB firmware flashing via Himax deployer
- reCamera: SSH-based reverse deployment (stop services, uninstall packages)
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class RestoreStatus(str, Enum):
    """Restore operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RestoreOperation:
    """Represents a single restore operation"""
    id: str
    device_type: str
    device_name: str
    status: RestoreStatus = RestoreStatus.PENDING
    progress: int = 0
    message: str = ""
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    logs: List[Dict[str, str]] = field(default_factory=list)


class RestoreManager:
    """Manages device restore operations"""

    def __init__(self):
        self.config_path = Path(__file__).parent.parent / "factory_firmware" / "restore_config.yaml"
        self.firmware_dir = Path(__file__).parent.parent / "factory_firmware"
        self._config: Optional[Dict[str, Any]] = None
        self._operations: Dict[str, RestoreOperation] = {}
        self._callbacks: Dict[str, Callable] = {}

    @property
    def config(self) -> Dict[str, Any]:
        """Load and cache restore configuration"""
        if self._config is None:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
            else:
                self._config = {"devices": {}}
        return self._config

    def get_supported_devices(self, lang: str = "en") -> List[Dict[str, Any]]:
        """Get list of supported devices for restore"""
        devices = []
        for device_id, device_config in self.config.get("devices", {}).items():
            name_key = "name_zh" if lang == "zh" else "name"
            desc_key = "description_zh" if lang == "zh" else "description"
            devices.append({
                "id": device_id,
                "name": device_config.get(name_key, device_config.get("name", device_id)),
                "description": device_config.get(desc_key, device_config.get("description", "")),
                "type": device_config.get("type", "unknown"),
            })
        return devices

    def get_device_config(self, device_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific device type"""
        return self.config.get("devices", {}).get(device_type)

    def get_operation(self, operation_id: str) -> Optional[RestoreOperation]:
        """Get restore operation by ID"""
        return self._operations.get(operation_id)

    def _add_log(self, operation: RestoreOperation, level: str, message: str):
        """Add log entry to operation"""
        operation.logs.append({
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        })
        logger.log(getattr(logging, level.upper(), logging.INFO), f"[{operation.id}] {message}")

    async def _notify_progress(self, operation: RestoreOperation):
        """Notify progress callback if registered"""
        callback = self._callbacks.get(operation.id)
        if callback:
            try:
                await callback({
                    "type": "progress",
                    "operation_id": operation.id,
                    "status": operation.status,
                    "progress": operation.progress,
                    "message": operation.message,
                    "current_step": operation.current_step,
                    "completed_steps": operation.completed_steps,
                    "total_steps": operation.total_steps,
                })
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    def register_callback(self, operation_id: str, callback: Callable):
        """Register progress callback for an operation"""
        self._callbacks[operation_id] = callback

    def unregister_callback(self, operation_id: str):
        """Unregister progress callback"""
        self._callbacks.pop(operation_id, None)

    async def start_restore(
        self,
        device_type: str,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> RestoreOperation:
        """Start a restore operation"""
        device_config = self.get_device_config(device_type)
        if not device_config:
            raise ValueError(f"Unsupported device type: {device_type}")

        # Create operation
        operation_id = str(uuid.uuid4())[:8]
        operation = RestoreOperation(
            id=operation_id,
            device_type=device_type,
            device_name=device_config.get("name", device_type),
            status=RestoreStatus.RUNNING,
            started_at=datetime.now(),
        )
        self._operations[operation_id] = operation

        if progress_callback:
            self.register_callback(operation_id, progress_callback)

        # Start restore in background
        restore_type = device_config.get("type", "")
        if restore_type == "watcher_dual_chip":
            asyncio.create_task(self._restore_watcher_dual(operation, device_config, connection))
        elif restore_type == "himax_usb":
            asyncio.create_task(self._restore_watcher(operation, device_config, connection))
        elif restore_type == "ssh_restore":
            asyncio.create_task(self._restore_recamera(operation, device_config, connection))
        else:
            operation.status = RestoreStatus.FAILED
            operation.error = f"Unknown restore type: {restore_type}"
            self._add_log(operation, "error", operation.error)

        return operation

    async def _restore_watcher(
        self,
        operation: RestoreOperation,
        device_config: Dict[str, Any],
        connection: Dict[str, Any],
    ):
        """Restore SenseCAP Watcher via USB firmware flashing"""
        try:
            from ..deployers.himax_deployer import HimaxDeployer
            from ..models.device import (
                DeviceConfig,
                FirmwareConfig,
                FirmwareSource,
                FlashConfig,
            )

            port = connection.get("port")
            if not port:
                raise ValueError("Serial port not specified")

            firmware_list = device_config.get("firmware", [])
            operation.total_steps = len(firmware_list) + 1  # +1 for detection
            operation.current_step = "Detecting device"
            operation.message = "Detecting Himax WE2 device..."
            await self._notify_progress(operation)

            # Create deployer
            deployer = HimaxDeployer()

            # Process each firmware file
            for i, fw_config in enumerate(firmware_list):
                if not fw_config.get("required", True):
                    continue

                fw_file = fw_config.get("file")
                fw_path = self.firmware_dir / fw_file

                if not fw_path.exists():
                    # Try to download firmware
                    source_url = fw_config.get("source_url")
                    if source_url:
                        operation.current_step = "Downloading firmware"
                        operation.message = f"Downloading {fw_config.get('name', 'firmware')}..."
                        await self._notify_progress(operation)
                        self._add_log(operation, "info", f"Downloading firmware from {source_url}")

                        success = await self._download_firmware(source_url, fw_path)
                        if not success:
                            raise FileNotFoundError(f"Failed to download firmware: {fw_file}")
                    else:
                        raise FileNotFoundError(f"Firmware file not found: {fw_file}")

                # Create device config for deployer
                flash_config = device_config.get("flash_config", {})
                device_cfg = DeviceConfig(
                    id="factory_restore",
                    name="Factory Restore",
                    type="himax_usb",
                    firmware=FirmwareConfig(
                        source=FirmwareSource(type="local", path=str(fw_path)),
                        flash_config=FlashConfig(
                            baudrate=flash_config.get("baudrate", 921600),
                            timeout=flash_config.get("timeout", 60),
                        ),
                    ),
                    solution_dir=str(self.firmware_dir),
                )

                # Flash firmware
                operation.current_step = f"Flashing {fw_config.get('name', 'firmware')}"
                operation.message = "Flashing firmware..."
                await self._notify_progress(operation)
                self._add_log(operation, "info", f"Flashing slot {fw_config.get('slot', 1)}: {fw_config.get('name')}")

                async def progress_handler(step: str, progress: int, message: str):
                    operation.message = message
                    operation.progress = int((operation.completed_steps + progress / 100) / operation.total_steps * 100)
                    await self._notify_progress(operation)

                success = await deployer.deploy(device_cfg, {"port": port}, progress_handler)

                if not success:
                    raise RuntimeError(f"Failed to flash {fw_config.get('name', 'firmware')}")

                operation.completed_steps += 1
                self._add_log(operation, "info", f"Successfully flashed {fw_config.get('name', 'firmware')}")

            # Complete
            operation.status = RestoreStatus.COMPLETED
            operation.progress = 100
            operation.message = "Restore completed successfully"
            operation.completed_at = datetime.now()
            self._add_log(operation, "info", "Watcher restore completed successfully")
            await self._notify_progress(operation)

        except Exception as e:
            operation.status = RestoreStatus.FAILED
            operation.error = str(e)
            operation.message = f"Restore failed: {str(e)}"
            operation.completed_at = datetime.now()
            self._add_log(operation, "error", f"Restore failed: {e}")
            await self._notify_progress(operation)
            logger.exception(f"Watcher restore failed: {e}")

        finally:
            self.unregister_callback(operation.id)

    async def _restore_watcher_dual(
        self,
        operation: RestoreOperation,
        device_config: Dict[str, Any],
        connection: Dict[str, Any],
    ):
        """Restore SenseCAP Watcher with both ESP32 and Himax firmware"""
        try:
            from ..deployers.esp32_deployer import ESP32Deployer
            from ..deployers.himax_deployer import HimaxDeployer
            from ..models.device import (
                DeviceConfig,
                FirmwareConfig,
                FirmwareSource,
                FlashConfig,
                PartitionConfig,
            )

            port = connection.get("port")
            if not port:
                raise ValueError("Serial port not specified")

            esp32_config = device_config.get("esp32", {})
            himax_config = device_config.get("himax", {})

            # Total steps: ESP32 detect + flash + Himax detect + flash
            operation.total_steps = 4
            operation.completed_steps = 0

            # ========== Step 1: Flash ESP32 ==========
            esp32_file = esp32_config.get("file")
            esp32_path = self.firmware_dir / esp32_file

            if not esp32_path.exists():
                raise FileNotFoundError(f"ESP32 firmware not found: {esp32_file}")

            operation.current_step = "Flashing ESP32"
            operation.message = "Preparing to flash ESP32-S3 firmware..."
            await self._notify_progress(operation)
            self._add_log(operation, "info", f"Starting ESP32-S3 firmware flash: {esp32_config.get('name')}")

            # Create ESP32 deployer
            esp32_deployer = ESP32Deployer()
            esp32_flash_config = esp32_config.get("flash_config", {})

            # Build device config for ESP32
            esp32_device_cfg = DeviceConfig(
                id="factory_restore_esp32",
                name="Factory Restore ESP32",
                type="esp32_usb",
                firmware=FirmwareConfig(
                    source=FirmwareSource(type="local", path=str(esp32_path)),
                    flash_config=FlashConfig(
                        chip=esp32_flash_config.get("chip", "esp32s3"),
                        baud_rate=esp32_flash_config.get("baud_rate", 921600),
                        flash_mode=esp32_flash_config.get("flash_mode", "dio"),
                        flash_freq=esp32_flash_config.get("flash_freq", "80m"),
                        flash_size=esp32_flash_config.get("flash_size", "16MB"),
                        partitions=[
                            PartitionConfig(
                                name="firmware",
                                offset=esp32_flash_config.get("address", "0x0"),
                                file=str(esp32_path),
                            )
                        ],
                    ),
                ),
                solution_dir=str(self.firmware_dir),
            )

            async def esp32_progress_handler(step: str, progress: int, message: str):
                if step == "detect":
                    operation.progress = int(progress * 0.125)  # 0-12.5%
                elif step == "flash":
                    operation.progress = int(12.5 + progress * 0.125)  # 12.5-25%
                operation.message = message
                await self._notify_progress(operation)

            # Flash ESP32
            esp32_success = await esp32_deployer.deploy(esp32_device_cfg, {"port": port}, esp32_progress_handler)

            if not esp32_success:
                raise RuntimeError("Failed to flash ESP32-S3 firmware")

            operation.completed_steps = 2
            self._add_log(operation, "info", "ESP32-S3 firmware flashed successfully")

            # Wait for device to reset and port to become available
            operation.message = "Waiting for device to reset..."
            await self._notify_progress(operation)
            await asyncio.sleep(3)

            # ========== Step 2: Flash Himax ==========
            himax_file = himax_config.get("file")
            himax_path = self.firmware_dir / himax_file

            if not himax_path.exists():
                raise FileNotFoundError(f"Himax firmware not found: {himax_file}")

            operation.current_step = "Flashing Himax"
            operation.message = "Preparing Himax WE2 firmware flash..."
            await self._notify_progress(operation)
            self._add_log(operation, "info", f"Starting Himax WE2 firmware flash: {himax_config.get('name')}")

            # Create Himax deployer
            himax_deployer = HimaxDeployer()
            himax_flash_config = himax_config.get("flash_config", {})

            # Build device config for Himax with ESP32 reset hold enabled
            # This is critical for SenseCAP Watcher - ESP32 must be held in reset
            # during Himax flashing to prevent interference
            himax_device_cfg = DeviceConfig(
                id="factory_restore_himax",
                name="Factory Restore Himax",
                type="himax_usb",
                firmware=FirmwareConfig(
                    source=FirmwareSource(type="local", path=str(himax_path)),
                    flash_config=FlashConfig(
                        baudrate=himax_flash_config.get("baudrate", 921600),
                        timeout=himax_flash_config.get("timeout", 60),
                        requires_esp32_reset_hold=True,  # Hold ESP32 in reset during Himax flash
                    ),
                ),
                solution_dir=str(self.firmware_dir),
            )

            async def himax_progress_handler(step: str, progress: int, message: str):
                # Himax progress: 50-100%
                operation.progress = int(50 + progress * 0.5)
                operation.message = message
                await self._notify_progress(operation)

            # Flash Himax (deployer will find ESP32 port and hold it in reset)
            himax_success = await himax_deployer.deploy(himax_device_cfg, {"port": port}, himax_progress_handler)

            if not himax_success:
                raise RuntimeError("Failed to flash Himax WE2 firmware")

            operation.completed_steps = 4
            self._add_log(operation, "info", "Himax WE2 firmware flashed successfully")

            # Complete
            operation.status = RestoreStatus.COMPLETED
            operation.progress = 100
            operation.message = "Restore completed successfully (ESP32 + Himax)"
            operation.completed_at = datetime.now()
            self._add_log(operation, "info", "Watcher dual-chip restore completed successfully")
            await self._notify_progress(operation)

        except Exception as e:
            operation.status = RestoreStatus.FAILED
            operation.error = str(e)
            operation.message = f"Restore failed: {str(e)}"
            operation.completed_at = datetime.now()
            self._add_log(operation, "error", f"Restore failed: {e}")
            await self._notify_progress(operation)
            logger.exception(f"Watcher dual-chip restore failed: {e}")

        finally:
            self.unregister_callback(operation.id)

    async def _restore_recamera(
        self,
        operation: RestoreOperation,
        device_config: Dict[str, Any],
        connection: Dict[str, Any],
    ):
        """Restore reCamera via SSH commands"""
        try:
            import paramiko

            host = connection.get("host")
            username = connection.get("username", device_config.get("default_credentials", {}).get("username", "root"))
            password = connection.get("password")
            port = connection.get("port", device_config.get("default_credentials", {}).get("port", 22))

            if not host:
                raise ValueError("Host not specified")
            if not password:
                raise ValueError("SSH password required")

            restore_ops = device_config.get("restore_operations", [])
            operation.total_steps = len(restore_ops)

            self._add_log(operation, "info", f"Connecting to {host}:{port} as {username}")
            operation.message = f"Connecting to {host}..."
            await self._notify_progress(operation)

            # Connect via SSH using paramiko
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            try:
                ssh.connect(
                    hostname=host,
                    port=port,
                    username=username,
                    password=password,
                    timeout=30,
                    allow_agent=False,
                    look_for_keys=False,
                )
                self._add_log(operation, "info", "SSH connection established")

                # Check remote OS is Linux
                operation.message = "Checking remote operating system..."
                await self._notify_progress(operation)

                stdin, stdout, stderr = ssh.exec_command("uname -s", timeout=30)
                os_name = stdout.read().decode('utf-8', errors='ignore').strip().lower()

                if os_name != "linux":
                    raise RuntimeError(
                        f"Remote device is not running Linux (detected: {os_name}). "
                        f"Only Linux devices are supported for restore operations."
                    )

                self._add_log(operation, "info", "Confirmed remote device is running Linux")

                for i, restore_op in enumerate(restore_ops):
                    op_name = restore_op.get("name", f"Step {i + 1}")
                    op_command = restore_op.get("command", "")

                    operation.current_step = op_name
                    operation.message = f"Executing: {op_name}"
                    operation.progress = int((i / operation.total_steps) * 100)
                    await self._notify_progress(operation)
                    self._add_log(operation, "info", f"Executing: {op_name}")

                    # Replace sudo with password-enabled sudo -S
                    # This handles commands that use 'sudo' which requires password
                    if 'sudo ' in op_command and password:
                        # Use printf to avoid echo issues with special characters
                        # Replace 'sudo ' with 'printf "password\n" | sudo -S '
                        escaped_password = password.replace("'", "'\"'\"'")
                        op_command = op_command.replace('sudo ', f"printf '%s\\n' '{escaped_password}' | sudo -S ")

                    # Execute command
                    try:
                        stdin, stdout, stderr = ssh.exec_command(op_command, timeout=60)
                        exit_status = stdout.channel.recv_exit_status()

                        stdout_text = stdout.read().decode('utf-8', errors='ignore').strip()
                        stderr_text = stderr.read().decode('utf-8', errors='ignore').strip()

                        if stdout_text:
                            self._add_log(operation, "info", f"Output: {stdout_text}")
                        if stderr_text and exit_status != 0:
                            self._add_log(operation, "warning", f"Stderr: {stderr_text}")

                        self._add_log(operation, "info", f"Completed: {op_name}")

                    except Exception as cmd_err:
                        self._add_log(operation, "warning", f"Error executing {op_name}: {cmd_err}")

                    operation.completed_steps = i + 1

                    # Small delay between operations
                    await asyncio.sleep(0.5)

            finally:
                ssh.close()

            # Complete
            operation.status = RestoreStatus.COMPLETED
            operation.progress = 100
            operation.message = "Restore completed successfully"
            operation.completed_at = datetime.now()
            self._add_log(operation, "info", "reCamera restore completed successfully")
            await self._notify_progress(operation)

        except paramiko.AuthenticationException as e:
            operation.status = RestoreStatus.FAILED
            operation.error = f"Authentication failed: {str(e)}"
            operation.message = "SSH authentication failed"
            operation.completed_at = datetime.now()
            self._add_log(operation, "error", f"SSH authentication error: {e}")
            await self._notify_progress(operation)
            logger.exception(f"reCamera restore auth error: {e}")

        except paramiko.SSHException as e:
            operation.status = RestoreStatus.FAILED
            operation.error = f"SSH error: {str(e)}"
            operation.message = f"SSH connection failed: {str(e)}"
            operation.completed_at = datetime.now()
            self._add_log(operation, "error", f"SSH error: {e}")
            await self._notify_progress(operation)
            logger.exception(f"reCamera restore SSH error: {e}")

        except Exception as e:
            operation.status = RestoreStatus.FAILED
            operation.error = str(e)
            operation.message = f"Restore failed: {str(e)}"
            operation.completed_at = datetime.now()
            self._add_log(operation, "error", f"Restore failed: {e}")
            await self._notify_progress(operation)
            logger.exception(f"reCamera restore failed: {e}")

        finally:
            self.unregister_callback(operation.id)

    async def _download_firmware(self, url: str, dest_path: Path) -> bool:
        """Download firmware file from URL"""
        try:
            import httpx

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                with open(dest_path, 'wb') as f:
                    f.write(response.content)

            logger.info(f"Downloaded firmware to {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download firmware from {url}: {e}")
            return False


# Global instance
_restore_manager: Optional[RestoreManager] = None


def get_restore_manager() -> RestoreManager:
    """Get the global restore manager instance"""
    global _restore_manager
    if _restore_manager is None:
        _restore_manager = RestoreManager()
    return _restore_manager
