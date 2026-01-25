"""
Himax WE2 firmware flashing deployer using sscma-micro or xmodem protocol
"""

import asyncio
import fnmatch
import logging
import re
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

import serial
import serial.tools.list_ports

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


class HimaxDeployer(BaseDeployer):
    """Himax WE2 firmware flashing via SSCMA tools or xmodem"""

    # Watcher Himax WE2 USB identifiers (WCH chip)
    # The Watcher exposes both wchusbserial (ESP32) and usbmodem (Himax) ports
    DEFAULT_VID = 0x1a86
    DEFAULT_PID = 0x55d2

    # Default port patterns
    DEFAULT_PORT_PATTERNS = [
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/ttyACM*",
        "COM*",  # Windows
    ]

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        port = connection.get("port")
        if not port:
            # Try auto-detection
            port = self._auto_detect_port(config)
            if not port:
                raise ValueError("No port specified and auto-detection failed for Himax device")
            logger.info(f"Auto-detected Himax port: {port}")

        if not config.firmware:
            raise ValueError("No firmware configuration")

        flash_config = config.firmware.flash_config
        firmware_source = config.firmware.source

        try:
            # Step 1: Detect device
            await self._report_progress(
                progress_callback, "detect", 0, "Detecting Himax WE2 device..."
            )

            if not self._verify_port_exists(port):
                await self._report_progress(
                    progress_callback, "detect", 0, f"Port {port} not found"
                )
                return False

            await self._report_progress(
                progress_callback, "detect", 100, f"Device detected on {port}"
            )

            # Step 2: Get firmware path
            firmware_path = config.get_asset_path(firmware_source.path)
            if not firmware_path:
                firmware_path = config.get_asset_path(f"assets/watcher_firmware/{Path(firmware_source.path).name}")

            if not firmware_path or not Path(firmware_path).exists():
                await self._report_progress(
                    progress_callback, "flash", 0, f"Firmware file not found: {firmware_source.path}"
                )
                return False

            # Step 3: Prompt user to press reset button
            await self._report_progress(
                progress_callback, "wait_reset", 0, "Please press the RESET button on the device..."
            )

            # Wait for bootloader mode
            bootloader_detected = await self._wait_for_bootloader(
                port,
                timeout=flash_config.timeout if hasattr(flash_config, 'timeout') else 30,
                progress_callback=progress_callback,
            )

            if not bootloader_detected:
                await self._report_progress(
                    progress_callback, "wait_reset", 0, "Bootloader not detected. Please try pressing RESET again."
                )
                # Continue anyway - user might have already pressed reset
                logger.warning("Bootloader detection timed out, attempting flash anyway")

            await self._report_progress(
                progress_callback, "wait_reset", 100, "Ready for flashing"
            )

            # Step 4: Flash firmware
            await self._report_progress(
                progress_callback, "flash", 0, "Starting firmware flash..."
            )

            baudrate = flash_config.baudrate if hasattr(flash_config, 'baudrate') else 921600

            # Try SSCMA tool first, fallback to xmodem
            success = await self._flash_with_sscma(
                port, firmware_path, baudrate, progress_callback
            )

            if not success:
                # Fallback to xmodem
                success = await self._flash_with_xmodem(
                    port, firmware_path, baudrate, progress_callback
                )

            if not success:
                await self._report_progress(
                    progress_callback, "flash", 0, "Flash failed"
                )
                return False

            await self._report_progress(
                progress_callback, "flash", 100, "Firmware flashed successfully"
            )

            # Step 5: Verify
            await self._report_progress(
                progress_callback, "verify", 100, "Deployment complete"
            )

            return True

        except Exception as e:
            logger.error(f"Himax deployment failed: {e}")
            await self._report_progress(
                progress_callback, "flash", 0, f"Deployment failed: {str(e)}"
            )
            return False

    def _auto_detect_port(self, config: DeviceConfig) -> Optional[str]:
        """Auto-detect Himax WE2 serial port"""
        detection = config.detection if hasattr(config, 'detection') else None

        # Method 1: VID/PID matching
        vid = None
        pid = None
        if detection:
            vid_str = getattr(detection, 'usb_vendor_id', None)
            pid_str = getattr(detection, 'usb_product_id', None)
            if vid_str:
                vid = int(vid_str, 16) if vid_str.startswith('0x') else int(vid_str)
            if pid_str:
                pid = int(pid_str, 16) if pid_str.startswith('0x') else int(pid_str)

        if not vid:
            vid = self.DEFAULT_VID
        if not pid:
            pid = self.DEFAULT_PID

        for port in serial.tools.list_ports.comports():
            if port.vid == vid and port.pid == pid:
                logger.info(f"Found Himax device by VID/PID: {port.device}")
                return port.device

        # Method 2: Port pattern matching
        patterns = self.DEFAULT_PORT_PATTERNS
        if detection and hasattr(detection, 'fallback_ports'):
            patterns = detection.fallback_ports + patterns

        for port in serial.tools.list_ports.comports():
            for pattern in patterns:
                if fnmatch.fnmatch(port.device, pattern):
                    # Prefer usbmodem ports for Himax
                    if 'usbmodem' in port.device.lower():
                        logger.info(f"Found Himax device by pattern: {port.device}")
                        return port.device

        # Last resort: return first matching pattern
        for port in serial.tools.list_ports.comports():
            for pattern in patterns:
                if fnmatch.fnmatch(port.device, pattern):
                    logger.info(f"Found potential Himax device: {port.device}")
                    return port.device

        return None

    def _verify_port_exists(self, port: str) -> bool:
        """Verify the port exists"""
        for p in serial.tools.list_ports.comports():
            if p.device == port:
                return True
        return False

    async def _wait_for_bootloader(
        self,
        port: str,
        timeout: int = 30,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Wait for device to enter bootloader mode"""
        try:
            ser = serial.Serial(
                port,
                baudrate=115200,
                timeout=1,
            )

            start_time = asyncio.get_event_loop().time()
            detected = False

            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    text = data.decode('utf-8', errors='ignore')
                    logger.debug(f"Bootloader output: {text}")

                    # Look for bootloader indicators
                    if any(marker in text.lower() for marker in ['boot', 'ready', 'xmodem', 'download']):
                        detected = True
                        break

                elapsed = int(asyncio.get_event_loop().time() - start_time)
                if progress_callback and elapsed % 5 == 0:
                    await self._report_progress(
                        progress_callback,
                        "wait_reset",
                        min(50, int(elapsed / timeout * 100)),
                        f"Waiting for reset button press... ({timeout - elapsed}s remaining)"
                    )

                await asyncio.sleep(0.5)

            ser.close()
            return detected

        except Exception as e:
            logger.warning(f"Error waiting for bootloader: {e}")
            return False

    async def _flash_with_sscma(
        self,
        port: str,
        firmware_path: str,
        baudrate: int,
        progress_callback: Optional[Callable],
    ) -> bool:
        """Flash using SSCMA CLI tool"""
        try:
            # Try sscma-micro CLI
            cmd = [
                "python", "-m", "sscma.cli",
                "flash",
                "--port", port,
                "--baudrate", str(baudrate),
                firmware_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            last_progress = 0
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if not line_str:
                    continue

                logger.debug(f"sscma: {line_str}")

                # Parse progress
                match = re.search(r'(\d+)%', line_str)
                if match and progress_callback:
                    progress = int(match.group(1))
                    if progress > last_progress:
                        await self._report_progress(
                            progress_callback, "flash", progress, f"Flashing... {progress}%"
                        )
                        last_progress = progress

            await process.wait()
            return process.returncode == 0

        except FileNotFoundError:
            logger.info("SSCMA CLI not found, trying alternative method")
            return False
        except Exception as e:
            logger.warning(f"SSCMA flash failed: {e}")
            return False

    async def _flash_with_xmodem(
        self,
        port: str,
        firmware_path: str,
        baudrate: int,
        progress_callback: Optional[Callable],
    ) -> bool:
        """Flash using xmodem protocol directly"""
        try:
            # Import xmodem library
            from xmodem import XMODEM

            ser = serial.Serial(
                port,
                baudrate=baudrate,
                timeout=10,
            )

            # Read firmware file
            firmware_size = Path(firmware_path).stat().st_size
            bytes_sent = 0

            def getc(size, timeout=1):
                return ser.read(size) or None

            def putc(data, timeout=1):
                nonlocal bytes_sent
                bytes_sent += len(data)
                return ser.write(data)

            modem = XMODEM(getc, putc)

            with open(firmware_path, 'rb') as f:
                # Send file
                def progress_handler(total, position):
                    if progress_callback:
                        progress = int(position / firmware_size * 100) if firmware_size > 0 else 0
                        asyncio.create_task(
                            self._report_progress(
                                progress_callback, "flash", progress, f"Flashing... {progress}%"
                            )
                        )

                success = modem.send(f, retry=16)

            ser.close()
            return success

        except ImportError:
            logger.warning("xmodem library not installed")
            return False
        except Exception as e:
            logger.error(f"xmodem flash failed: {e}")
            return False

    @classmethod
    def list_available_ports(cls) -> List[Dict[str, Any]]:
        """List available serial ports that might be Himax devices"""
        ports = []
        for port in serial.tools.list_ports.comports():
            is_himax = False
            if port.vid == cls.DEFAULT_VID and port.pid == cls.DEFAULT_PID:
                is_himax = True
            elif 'usbmodem' in port.device.lower():
                is_himax = True

            if is_himax:
                ports.append({
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid,
                    "vid": port.vid,
                    "pid": port.pid,
                })

        return ports
