"""
Device Restore Manager Service

Handles restoring devices to factory state:
- SenseCAP Watcher: USB firmware flashing via Himax deployer
- reCamera: SSH-based reverse deployment (stop services, uninstall packages)
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

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
        if restore_type == "himax_usb":
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
            from ..models.device import DeviceConfig, FirmwareConfig, FlashConfig, FirmwareSource

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
                operation.message = "Please press the RESET button on the device..."
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

                for i, restore_op in enumerate(restore_ops):
                    op_name = restore_op.get("name", f"Step {i + 1}")
                    op_command = restore_op.get("command", "")

                    operation.current_step = op_name
                    operation.message = f"Executing: {op_name}"
                    operation.progress = int((i / operation.total_steps) * 100)
                    await self._notify_progress(operation)
                    self._add_log(operation, "info", f"Executing: {op_name}")

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
            operation.message = f"SSH authentication failed"
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
