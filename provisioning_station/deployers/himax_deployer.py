"""
Himax WE2 firmware flashing deployer using xmodem protocol

IMPORTANT: SenseCAP Watcher requires special handling!
The Watcher's ESP32 firmware monitors Himax and will reset it when detecting anomalies
(like entering download mode). This causes flashing to fail.

Solution: Hold ESP32 in reset state (DTR=False) during Himax flashing.
"""

import asyncio
import fnmatch
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import serial
import serial.tools.list_ports

from ..models.device import DeviceConfig, HimaxModelConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)

# Preamble magic bytes for multi-model flashing
PREAMBLE_HEADER = bytes([0xC0, 0x5A])
PREAMBLE_FOOTER = bytes([0x5A, 0xC0])


class HimaxDeployer(BaseDeployer):
    """Himax WE2 firmware flashing via xmodem protocol"""

    # Watcher Himax WE2 USB identifiers (WCH chip)
    DEFAULT_VID = 0x1a86
    DEFAULT_PID = 0x55d2

    # Default port patterns
    DEFAULT_PORT_PATTERNS = [
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/ttyACM*",
        "COM*",  # Windows
    ]

    # ESP32 port patterns (for SenseCAP Watcher safe flashing)
    ESP32_PORT_PATTERNS = [
        "/dev/cu.wchusbserial*",
        "/dev/tty.wchusbserial*",
        "/dev/ttyUSB*",
    ]

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        port = connection.get("port")
        if not port:
            port = self._auto_detect_port(config)
            if not port:
                raise ValueError("No port specified and auto-detection failed for Himax device")
            logger.info(f"Auto-detected Himax port: {port}")

        if not config.firmware:
            raise ValueError("No firmware configuration")

        flash_config = config.firmware.flash_config
        firmware_source = config.firmware.source

        # Check if this requires ESP32 reset hold (SenseCAP Watcher)
        requires_esp32_hold = False
        if hasattr(flash_config, 'requires_esp32_reset_hold'):
            requires_esp32_hold = flash_config.requires_esp32_reset_hold
        logger.info(f"Flash config: requires_esp32_reset_hold={requires_esp32_hold}")

        esp32_serial = None

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

            # Step 1.4: Wait for port to be available (may be occupied by other programs)
            await self._report_progress(
                progress_callback, "detect", 100, "Checking port availability..."
            )

            if not await self._wait_for_port_available(
                port,
                timeout=10,
                auto_release=True,
                progress_callback=progress_callback
            ):
                await self._report_progress(
                    progress_callback, "detect", 0,
                    f"Port {port} is busy. Please ensure no other program is using it."
                )
                return False

            # Step 1.5: Find ESP32 companion port if needed
            esp32_port = None
            if requires_esp32_hold:
                esp32_port = self._find_companion_esp32_port(port)
                if esp32_port:
                    await self._report_progress(
                        progress_callback, "detect", 100,
                        f"Found ESP32 port: {esp32_port}"
                    )
                else:
                    logger.warning("ESP32 port not found, flashing may be unstable")

            # Step 2: Get firmware path
            firmware_path = config.get_asset_path(firmware_source.path)
            if not firmware_path:
                firmware_path = config.get_asset_path(f"assets/watcher_firmware/{Path(firmware_source.path).name}")

            if not firmware_path or not Path(firmware_path).exists():
                await self._report_progress(
                    progress_callback, "flash", 0, f"Firmware file not found: {firmware_source.path}"
                )
                return False

            # Step 3: Ready for flashing
            await self._report_progress(
                progress_callback, "prepare", 100, "Ready for flashing"
            )

            # Step 4: Flash firmware using xmodem
            await self._report_progress(
                progress_callback, "flash", 0, "Starting firmware flash..."
            )

            baudrate = flash_config.baudrate if hasattr(flash_config, 'baudrate') else 921600

            # Get user-selected models (if any)
            selected_model_ids = connection.get("selected_models", [])
            models_config = getattr(flash_config, 'models', [])
            models_to_flash = self._get_models_to_flash(models_config, selected_model_ids)

            # Get protocol type (xmodem or xmodem1k)
            protocol = getattr(flash_config, 'protocol', 'xmodem')

            # Use multi-model flashing if models are configured
            if models_to_flash:
                success = await self._flash_with_xmodem_multimodel(
                    port=port,
                    firmware_path=firmware_path,
                    baudrate=baudrate,
                    protocol=protocol,
                    models=models_to_flash,
                    base_path=config.base_path,
                    progress_callback=progress_callback,
                    esp32_port=esp32_port
                )
            else:
                success = await self._flash_with_xmodem(
                    port, firmware_path, baudrate, progress_callback, esp32_port
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
        """Auto-detect Himax WE2 serial port

        IMPORTANT: SenseCAP Watcher exposes multiple serial ports:
        - usbmodem* with VID:PID 1A86:55D2 for Himax WE2 (what we want)
        - wchusbserial* for ESP32-S3 (NOT what we want)

        There may be OTHER usbmodem devices with different VID/PID - we must
        check VID/PID to ensure we get the correct Watcher port.

        Priority:
        1. VID/PID match + usbmodem pattern (most reliable)
        2. VID/PID match + fallback patterns
        3. Fallback to any usbmodem with matching VID/PID
        """
        detection = config.detection if hasattr(config, 'detection') else None

        # Get expected VID/PID
        vid = self.DEFAULT_VID
        pid = self.DEFAULT_PID
        if detection:
            vid_str = getattr(detection, 'usb_vendor_id', None)
            pid_str = getattr(detection, 'usb_product_id', None)
            if vid_str:
                vid = int(vid_str, 16) if vid_str.startswith('0x') else int(vid_str)
            if pid_str:
                pid = int(pid_str, 16) if pid_str.startswith('0x') else int(pid_str)

        patterns = self.DEFAULT_PORT_PATTERNS
        if detection and hasattr(detection, 'fallback_ports') and detection.fallback_ports:
            patterns = detection.fallback_ports + patterns

        # Method 1: VID/PID match + usbmodem pattern (most reliable for Watcher)
        # This ensures we get the Watcher's Himax port, not some other usbmodem device
        # Watcher has two usbmodem ports: ending with '1' (Himax) and '3' (another interface)
        # We need to prefer the one ending with '1'
        usbmodem_candidates = []
        for port in serial.tools.list_ports.comports():
            if port.vid == vid and port.pid == pid:
                if 'usbmodem' in port.device.lower():
                    for pattern in patterns:
                        if fnmatch.fnmatch(port.device, pattern):
                            usbmodem_candidates.append(port.device)

        if usbmodem_candidates:
            # Sort to prefer ports ending with '1' over '3' (Himax vs ESP32 interface)
            usbmodem_candidates.sort(key=lambda x: x[-1])
            selected = usbmodem_candidates[0]
            logger.info(f"Found Himax device by VID/PID + usbmodem: {selected}")
            if len(usbmodem_candidates) > 1:
                logger.debug(f"Other candidates: {usbmodem_candidates[1:]}")
            return selected

        # Method 2: VID/PID match + any pattern (excluding wchusbserial)
        for port in serial.tools.list_ports.comports():
            if port.vid == vid and port.pid == pid:
                if 'wchusbserial' in port.device.lower():
                    continue
                for pattern in patterns:
                    if fnmatch.fnmatch(port.device, pattern):
                        logger.info(f"Found Himax device by VID/PID: {port.device}")
                        return port.device

        # Method 3: Fallback - usbmodem pattern only (without VID/PID check)
        # This is less reliable but kept for backwards compatibility
        for port in serial.tools.list_ports.comports():
            if 'usbmodem' in port.device.lower():
                # Skip if we know this is a different device
                if port.vid and port.vid != vid:
                    logger.debug(f"Skipping {port.device} - different VID {port.vid:#x}")
                    continue
                for pattern in patterns:
                    if fnmatch.fnmatch(port.device, pattern):
                        logger.info(f"Found Himax device by usbmodem pattern: {port.device}")
                        return port.device

        return None

    def _verify_port_exists(self, port: str) -> bool:
        """Verify the port exists"""
        for p in serial.tools.list_ports.comports():
            if p.device == port:
                return True
        return False

    async def _wait_for_port_available(
        self,
        port: str,
        timeout: int = 10,
        auto_release: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Wait for serial port to become available, optionally auto-releasing occupied ports.

        Args:
            port: Serial port path
            timeout: Seconds to wait for port availability
            auto_release: If True, automatically terminate processes using the port
            progress_callback: Optional callback for progress updates
        """
        # Lazy import to avoid circular dependency
        from ..services.serial_port_manager import SerialPortManager

        start_time = time.time()
        attempt = 0

        while (time.time() - start_time) < timeout:
            attempt += 1

            # FIRST: Check with lsof if any process is using the port
            # This is more reliable than pyserial for detecting exclusive locks
            if auto_release:
                proc_info = await SerialPortManager.get_process_using_port_async(port)

                if proc_info:
                    logger.debug(
                        f"Port {port} is used by {proc_info['name']} "
                        f"(PID: {proc_info['pid']})"
                    )
                    if progress_callback:
                        await self._report_progress(
                            progress_callback, "detect", 0,
                            f"Port {port} is used by {proc_info['name']} "
                            f"(PID: {proc_info['pid']}), releasing..."
                        )

                    released = await SerialPortManager.release_port_async(port)
                    if released:
                        logger.debug(f"Port {port} released successfully")
                        if progress_callback:
                            await self._report_progress(
                                progress_callback, "detect", 0,
                                f"Port {port} released successfully"
                            )
                        # Wait a moment for OS to fully release the port
                        await asyncio.sleep(1.0)
                    else:
                        logger.warning(f"Failed to release port {port}")
                        await asyncio.sleep(0.5)
                        continue

            # THEN: Try to open the port to verify it's truly available
            try:
                ser = serial.Serial()
                ser.port = port
                ser.baudrate = 115200
                ser.timeout = 0.1
                ser.exclusive = True  # Request exclusive access
                ser.open()
                ser.close()
                logger.debug(f"Port {port} is available (attempt {attempt})")
                return True
            except serial.SerialException as e:
                error_str = str(e).lower()
                is_busy = (
                    "resource temporarily unavailable" in error_str or
                    "busy" in error_str or
                    "access is denied" in error_str or  # Windows
                    "permission denied" in error_str or
                    "exclusively lock" in error_str
                )

                if is_busy:
                    logger.debug(f"Port {port} busy, waiting... (attempt {attempt})")
                    await asyncio.sleep(0.5)
                else:
                    # Other error (port doesn't exist, etc.)
                    logger.warning(f"Port {port} error: {e}")
                    return False
            except Exception as e:
                logger.warning(f"Unexpected error checking port {port}: {e}")
                return False

        logger.warning(f"Timeout waiting for port {port} to become available")
        return False

    def _find_companion_esp32_port(self, himax_port: str) -> Optional[str]:
        """Find the companion ESP32 serial port for SenseCAP Watcher.

        On macOS: Look for wchusbserial port paired with usbmodem port
        On Windows: Look for another COM port from the same WCH USB hub (same serial number)

        The Watcher has two USB interfaces:
        - Interface for Himax WE2 (what we flash)
        - Interface for ESP32 (needs to be held in reset during flash)
        """
        logger.debug(f"Looking for companion ESP32 port for Himax: {himax_port}")

        # Get the Himax port info to find its serial number
        himax_port_info = None
        for port in serial.tools.list_ports.comports():
            if port.device == himax_port:
                himax_port_info = port
                break

        if himax_port_info:
            logger.debug(
                f"Himax port info: device={himax_port_info.device}, "
                f"serial={himax_port_info.serial_number}, "
                f"location={himax_port_info.location}"
            )

        # === Windows: Find companion COM port by serial number or location ===
        if himax_port.upper().startswith("COM"):
            if himax_port_info and himax_port_info.serial_number:
                # Find another port with the same serial number (same USB device)
                for port in serial.tools.list_ports.comports():
                    if port.device != himax_port and port.serial_number == himax_port_info.serial_number:
                        logger.info(f"Found ESP32 port by serial number: {port.device}")
                        return port.device

            # Fallback: Find port with same VID/PID but different interface
            if himax_port_info and himax_port_info.vid and himax_port_info.pid:
                for port in serial.tools.list_ports.comports():
                    if (port.device != himax_port and
                        port.vid == himax_port_info.vid and
                        port.pid == himax_port_info.pid):
                        logger.info(f"Found ESP32 port by VID/PID: {port.device}")
                        return port.device

            # Last resort on Windows: look for adjacent COM port numbers
            # WCH chips often enumerate as consecutive COM ports
            com_match = re.search(r'COM(\d+)', himax_port.upper())
            if com_match:
                himax_num = int(com_match.group(1))
                # Check COM ports within ±2 range
                for offset in [1, -1, 2, -2]:
                    candidate = f"COM{himax_num + offset}"
                    for port in serial.tools.list_ports.comports():
                        if port.device.upper() == candidate:
                            # Verify it's likely from the same device (same VID or similar description)
                            if (himax_port_info and port.vid == himax_port_info.vid):
                                logger.info(f"Found ESP32 port by adjacent COM number: {port.device}")
                                return port.device

            logger.warning("Could not find ESP32 companion port on Windows")
            return None

        # === Linux: Find companion port by serial number, VID/PID, or ttyUSB pattern ===
        if himax_port.startswith("/dev/tty"):
            # Method 1: Find by serial number (most reliable)
            if himax_port_info and himax_port_info.serial_number:
                for port in serial.tools.list_ports.comports():
                    if port.device != himax_port and port.serial_number == himax_port_info.serial_number:
                        logger.info(f"Found ESP32 port by serial number: {port.device}")
                        return port.device

            # Method 2: Find by VID/PID
            if himax_port_info and himax_port_info.vid and himax_port_info.pid:
                for port in serial.tools.list_ports.comports():
                    if (port.device != himax_port and
                        port.vid == himax_port_info.vid and
                        port.pid == himax_port_info.pid):
                        logger.info(f"Found ESP32 port by VID/PID: {port.device}")
                        return port.device

            # Method 3: For ttyACM ports, look for adjacent numbers
            # Linux often enumerates composite USB devices as ttyACM0, ttyACM1, etc.
            acm_match = re.search(r'/dev/ttyACM(\d+)', himax_port)
            if acm_match:
                himax_num = int(acm_match.group(1))
                for offset in [1, -1, 2, -2]:
                    candidate = f"/dev/ttyACM{himax_num + offset}"
                    for port in serial.tools.list_ports.comports():
                        if port.device == candidate:
                            if himax_port_info and port.vid == himax_port_info.vid:
                                logger.info(f"Found ESP32 port by adjacent ttyACM number: {port.device}")
                                return port.device

            # Method 4: For ttyUSB ports (if Himax is on ttyACM, ESP32 might be on ttyUSB)
            # WCH chips on Linux can appear as either ttyACM or ttyUSB
            if 'ttyACM' in himax_port:
                for port in serial.tools.list_ports.comports():
                    if 'ttyUSB' in port.device:
                        if himax_port_info and port.vid == himax_port_info.vid:
                            logger.info(f"Found ESP32 port on ttyUSB: {port.device}")
                            return port.device

            logger.warning("Could not find ESP32 companion port on Linux")
            return None

        # === macOS: Original usbmodem/wchusbserial logic ===
        match = re.search(r'usbmodem(\w+)', himax_port)
        if not match:
            return None

        himax_serial = match.group(1)
        himax_base = himax_serial[:10] if len(himax_serial) > 10 else himax_serial[:-2]
        himax_suffix = himax_serial[-2:] if len(himax_serial) > 2 else himax_serial

        logger.debug(f"Himax serial: {himax_serial}, base: {himax_base}, suffix: {himax_suffix}")

        # Find ESP32 port with DIFFERENT suffix (different USB interface)
        for port in serial.tools.list_ports.comports():
            if 'wchusbserial' in port.device.lower():
                esp_match = re.search(r'wchusbserial(\w+)', port.device)
                if esp_match:
                    esp_serial = esp_match.group(1)
                    esp_suffix = esp_serial[-2:] if len(esp_serial) > 2 else esp_serial

                    # Same device but different interface
                    if esp_suffix != himax_suffix:
                        logger.info(f"Found ESP32 port: {port.device}")
                        return port.device

        # Fallback: return any wchusbserial port
        for port in serial.tools.list_ports.comports():
            if 'wchusbserial' in port.device.lower():
                logger.info(f"Using fallback ESP32 port: {port.device}")
                return port.device

        return None

    def _hold_esp32_reset(self, esp32_port: str) -> Optional[serial.Serial]:
        """Hold ESP32 in reset state by controlling DTR pin."""
        try:
            ser = serial.Serial()
            ser.port = esp32_port
            ser.baudrate = 115200
            ser.dtr = False  # EN pin - False = hold in reset
            ser.rts = True   # GPIO0 - True = download mode
            ser.open()
            logger.info(f"Holding ESP32 in reset on {esp32_port}")
            return ser
        except Exception as e:
            logger.warning(f"Could not hold ESP32 in reset: {e}")
            return None

    def _release_esp32_reset(self, ser: serial.Serial):
        """Release ESP32 from reset state"""
        try:
            ser.dtr = True   # Release EN pin
            ser.rts = False  # Release GPIO0
            time.sleep(0.1)
            ser.close()
            logger.info("Released ESP32 from reset")
        except Exception as e:
            logger.warning(f"Error releasing ESP32 reset: {e}")

    def _open_serial_port(self, port: str, baudrate: int, timeout: int = 60) -> serial.Serial:
        """Open serial port with proper settings matching official xmodem_send.py

        Critical settings:
        - xonxoff=0, rtscts=0: Disable flow control (essential!)
        - timeout=60: Long timeout for stable communication
        """
        ser = serial.Serial()
        ser.port = port
        ser.timeout = timeout
        ser.baudrate = baudrate
        ser.bytesize = serial.EIGHTBITS
        ser.stopbits = serial.STOPBITS_ONE
        ser.xonxoff = 0  # Disable XON/XOFF flow control
        ser.rtscts = 0   # Disable RTS/CTS flow control
        ser.parity = serial.PARITY_NONE
        ser.open()
        ser.flushInput()
        ser.flushOutput()
        return ser

    def _send_at_command(self, ser: serial.Serial, command: str):
        """Send AT command with carriage return (matching official script)"""
        ser.write(bytes(command + "\r", encoding='ascii'))

    async def _flash_with_xmodem(
        self,
        port: str,
        firmware_path: str,
        baudrate: int,
        progress_callback: Optional[Callable],
        esp32_port: Optional[str] = None,
    ) -> bool:
        """Flash using xmodem protocol with proper Himax bootloader handshake

        Protocol (matching official xmodem_send.py):
        1. Hold ESP32 in reset (if SenseCAP Watcher)
        2. Open serial port with proper settings
        3. Send "1" repeatedly until "Send data using the xmodem protocol"
        4. sleep(1), flushInput(), send "1" again
        5. Let xmodem library handle the 'C' handshake
        6. Transfer firmware using xmodem
        7. Wait for reboot prompt and send "y"
        8. Release ESP32 from reset
        """
        esp32_serial = None

        try:
            # Step 0: Hold ESP32 in reset if this is SenseCAP Watcher
            if esp32_port:
                esp32_serial = self._hold_esp32_reset(esp32_port)
                if esp32_serial:
                    await self._report_progress(
                        progress_callback, "flash", 5, "ESP32 held in reset"
                    )
                    # Give it a moment to stabilize
                    await asyncio.sleep(0.5)

            # Step 1: Open Himax serial port with proper settings
            await self._report_progress(
                progress_callback, "flash", 10, "Connecting to Himax..."
            )

            ser = self._open_serial_port(port, baudrate, timeout=60)
            logger.info(f"Opened Himax port: {port}")

            # Step 2: Wait for bootloader and send "1" to select xmodem download
            await self._report_progress(
                progress_callback, "flash", 15, "Waiting for bootloader..."
            )

            # Use short timeout for rapid polling during bootloader detection
            ser.timeout = 0.5  # 500ms for each readline

            bootloader_ready = False
            start_time = time.time()
            timeout_sec = 30

            while (time.time() - start_time) < timeout_sec:
                response = ser.readline().strip()
                if response:
                    logger.debug(f"Device: {response}")
                self._send_at_command(ser, '1')

                # Match official script: look for "Send data using the xmodem protocol"
                if b'Send data using the xmodem protocol' in response:
                    bootloader_ready = True
                    break

            # Restore timeout for xmodem transfer
            ser.timeout = 60

            if not bootloader_ready:
                logger.error("Timeout waiting for bootloader")
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 30, "Bootloader ready"
            )

            # Step 3: Match official script sequence exactly
            # sleep(1), flushInput(), send '1' again, then start xmodem
            await asyncio.sleep(1)
            ser.flushInput()
            self._send_at_command(ser, '1')

            await self._report_progress(
                progress_callback, "flash", 40, "Starting transfer..."
            )

            # Step 4: Transfer firmware using xmodem
            # Let xmodem library handle the 'C' handshake internally
            from xmodem import XMODEM

            # Match official xmodem_send.py - don't convert empty reads to None
            def getc(size, timeout=1):
                return ser.read(size)

            def putc(data, timeout=1):
                return ser.write(data)

            modem = XMODEM(getc, putc, mode="xmodem")

            with open(firmware_path, "rb") as f:
                success = modem.send(f, retry=16, quiet=True)

            if not success:
                logger.error("Xmodem transfer failed")
                ser.close()
                return False

            logger.info("Xmodem transfer complete")
            await self._report_progress(
                progress_callback, "flash", 90, "Transfer complete"
            )

            # Step 5: Wait for reboot prompt and confirm
            start_time = time.time()
            timeout_sec = 60

            while (time.time() - start_time) < timeout_sec:
                response = ser.readline().strip()
                if response:
                    logger.debug(f"Device: {response}")
                # Use shorter pattern to handle split reads
                if b"reboot system? (y)" in response or b"end file transmission" in response:
                    self._send_at_command(ser, 'y')
                    logger.info("Sent reboot confirmation")
                    break

            ser.close()

            await self._report_progress(
                progress_callback, "flash", 100, "Flash complete!"
            )

            return True

        except ImportError:
            logger.error("xmodem library not installed")
            await self._report_progress(
                progress_callback, "flash", 0, "xmodem library not installed"
            )
            return False
        except Exception as e:
            logger.error(f"xmodem flash failed: {e}")
            return False
        finally:
            # Always release ESP32 from reset
            if esp32_serial:
                self._release_esp32_reset(esp32_serial)
                logger.info("ESP32 released from reset")

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

    def _get_models_to_flash(
        self,
        models_config: List[HimaxModelConfig],
        selected_ids: List[str]
    ) -> List[HimaxModelConfig]:
        """Determine which models to flash based on user selection"""
        if not models_config:
            return []
        if selected_ids:
            # User made explicit selection
            return [m for m in models_config if m.id in selected_ids]
        else:
            # Default: flash required=True or default=True models
            return [m for m in models_config if m.required or m.default]

    def _generate_preamble(
        self,
        flash_address: str,
        offset: str,
        packet_size: int = 128
    ) -> bytes:
        """Generate preamble packet for model flashing

        Preamble format:
          [0xC0, 0x5A]           - 2 bytes magic header
          [flash_address]        - 4 bytes, little-endian
          [offset]               - 4 bytes, little-endian
          [0x5A, 0xC0]           - 2 bytes magic footer
          [0xFF * padding]       - fill to packet_size
        """
        addr = int(flash_address, 16)
        off = int(offset, 16)

        preamble = PREAMBLE_HEADER
        preamble += addr.to_bytes(4, 'little')
        preamble += off.to_bytes(4, 'little')
        preamble += PREAMBLE_FOOTER
        preamble += bytes([0xFF] * (packet_size - 12))

        return preamble

    async def _wait_for_reboot_prompt(
        self,
        ser: serial.Serial,
        timeout: int = 60
    ) -> bool:
        """Wait for the reboot confirmation prompt from bootloader

        Use shorter readline timeout to allow multiple retries within overall timeout.
        """
        old_timeout = ser.timeout
        ser.timeout = 5  # Shorter timeout for multiple retries
        start = time.time()
        retry_count = 0

        try:
            while (time.time() - start) < timeout:
                retry_count += 1
                try:
                    response = ser.readline()
                    if response:
                        response_str = response.strip()
                        if response_str:
                            # Log readable text
                            try:
                                text = response_str.decode('ascii', errors='ignore')
                                if text:
                                    logger.debug(f"Device: {text}")
                            except:
                                pass

                        # Check for prompt - use shorter patterns
                        if b"reboot system? (y)" in response or b"end file transmission" in response:
                            return True
                    else:
                        # Empty response - log occasionally for debugging
                        if retry_count % 6 == 1:  # Every 30 seconds
                            logger.debug(f"Waiting for device response... ({int(time.time() - start)}s elapsed)")
                except Exception as e:
                    logger.debug(f"readline error: {e}")

            logger.error(f"Timeout after {timeout}s waiting for reboot prompt (tried {retry_count} times)")
        finally:
            ser.timeout = old_timeout

        return False

    async def _wait_for_bootloader(
        self,
        ser: serial.Serial,
        timeout: int = 30
    ) -> bool:
        """Wait for bootloader and enter xmodem download mode

        Matches official xmodem_send.py behavior:
        - Use readline() with timeout
        - Send "1\r" command
        - Look for "Send data using the xmodem protocol"

        Note: Use short serial timeout (0.5s) for rapid polling during detection,
        then restore to 60s for actual xmodem transfer.
        """
        # Use shorter timeout for rapid polling during bootloader detection
        old_timeout = ser.timeout
        ser.timeout = 0.5  # 500ms timeout for each readline

        start_time = time.time()

        try:
            while (time.time() - start_time) < timeout:
                response = ser.readline().strip()
                if response:
                    logger.debug(f"Device: {response}")
                self._send_at_command(ser, '1')

                # Match official script: look for "Send data using the xmodem protocol"
                if b'Send data using the xmodem protocol' in response:
                    return True
        finally:
            # Restore original timeout for xmodem transfer
            ser.timeout = old_timeout

        logger.error("Timeout waiting for bootloader")
        return False

    def _prepare_for_xmodem(self, ser: serial.Serial):
        """Prepare serial port for xmodem transfer (matching official script)

        After detecting bootloader ready:
        1. sleep(1)
        2. flushInput()
        3. send '1' command
        Then let xmodem library handle the 'C' handshake
        """
        time.sleep(1)
        ser.flushInput()
        self._send_at_command(ser, '1')

    def _resolve_model_path(self, model: HimaxModelConfig, base_path: str) -> str:
        """Resolve model file path (local or download)"""
        local_path = Path(base_path) / model.path
        if local_path.exists():
            return str(local_path)

        # If URL is provided, download the model
        if model.url:
            return self._download_model(model)

        raise FileNotFoundError(f"Model file not found: {model.path}")

    def _download_model(self, model: HimaxModelConfig) -> str:
        """Download model file to temporary directory with caching"""
        import tempfile
        import urllib.request

        cache_dir = Path(tempfile.gettempdir()) / "himax_models"
        cache_dir.mkdir(exist_ok=True)

        filename = Path(model.path).name
        cache_path = cache_dir / filename

        if not cache_path.exists():
            logger.info(f"Downloading model: {model.url}")
            urllib.request.urlretrieve(model.url, cache_path)
            # TODO: Validate checksum if provided

        return str(cache_path)

    async def _flash_with_xmodem_multimodel(
        self,
        port: str,
        firmware_path: str,
        baudrate: int,
        protocol: str,
        models: List[HimaxModelConfig],
        base_path: str,
        progress_callback: Optional[Callable],
        esp32_port: Optional[str] = None,
    ) -> bool:
        """Flash base firmware followed by multiple AI models

        Protocol flow (matching official xmodem_send.py):
        1. Enter bootloader (send '1\r', wait for xmodem prompt)
        2. sleep(1), flushInput(), send '1\r' again
        3. Send base firmware via xmodem (library handles 'C' handshake)
        4. For each model:
           a. Wait for reboot prompt, send 'n\r' to continue
           b. Send preamble packet with flash address
           c. Wait for reboot prompt, send 'n\r'
           d. Send model file via xmodem
        5. After all models, send 'y\r' to reboot
        """
        packet_size = 128 if protocol == "xmodem" else 1024
        esp32_serial = None

        try:
            # Step 0: Hold ESP32 in reset if this is SenseCAP Watcher
            if esp32_port:
                esp32_serial = self._hold_esp32_reset(esp32_port)
                if esp32_serial:
                    await self._report_progress(
                        progress_callback, "flash", 5, "ESP32 held in reset"
                    )
                    await asyncio.sleep(0.5)

            # Step 1: Open Himax serial port with proper settings
            await self._report_progress(
                progress_callback, "flash", 10, "Connecting to Himax..."
            )

            ser = self._open_serial_port(port, baudrate, timeout=60)
            logger.info(f"Opened Himax port: {port}")

            # Step 2: Wait for bootloader
            await self._report_progress(
                progress_callback, "flash", 15, "Waiting for bootloader..."
            )

            if not await self._wait_for_bootloader(ser, timeout=30):
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 20, "Bootloader ready"
            )

            # Step 3: Prepare for xmodem (matching official script sequence)
            self._prepare_for_xmodem(ser)

            await self._report_progress(
                progress_callback, "flash", 25, "Starting base firmware transfer..."
            )

            # Step 4: Transfer base firmware using xmodem
            # Let xmodem library handle the 'C' handshake internally
            from xmodem import XMODEM

            # Match official xmodem_send.py - don't convert empty reads to None
            def getc(size, timeout=1):
                return ser.read(size)

            def putc(data, timeout=1):
                return ser.write(data)

            modem = XMODEM(getc, putc, mode=protocol)

            # Run blocking xmodem in thread to allow WebSocket updates
            def send_firmware():
                with open(firmware_path, "rb") as f:
                    return modem.send(f, retry=16, quiet=True)

            if not await asyncio.to_thread(send_firmware):
                logger.error("Base firmware xmodem transfer failed")
                ser.close()
                return False

            logger.info("Base firmware transfer complete")
            await self._report_progress(
                progress_callback, "flash", 35, "Base firmware complete"
            )

            # Step 5: Flash each model
            if models:
                total_models = len(models)
                for idx, model in enumerate(models):
                    progress_base = 35 + int((idx / total_models) * 55)
                    model_name = model.name_zh if model.name_zh else model.name

                    await self._report_progress(
                        progress_callback, "flash", progress_base,
                        f"Flashing model {idx + 1}/{total_models}: {model_name}"
                    )

                    # Resolve model path first to fail fast
                    try:
                        model_path = self._resolve_model_path(model, base_path)
                        logger.info(f"Model file resolved: {model_path}")
                    except FileNotFoundError as e:
                        logger.error(f"Model file not found: {e}")
                        await self._report_progress(
                            progress_callback, "flash", progress_base,
                            f"Model file not found: {model.path}"
                        )
                        ser.close()
                        return False

                    # Wait for reboot prompt
                    await self._report_progress(
                        progress_callback, "flash", progress_base,
                        f"[{idx + 1}/{total_models}] Waiting for reboot prompt..."
                    )
                    if not await self._wait_for_reboot_prompt(ser, timeout=60):
                        logger.error(f"Timeout waiting for reboot prompt before model {model.id}")
                        await self._report_progress(
                            progress_callback, "flash", progress_base,
                            "Timeout waiting for reboot prompt"
                        )
                        ser.close()
                        return False

                    # Send 'n' to continue (not reboot) - matching official script
                    await asyncio.sleep(1)
                    ser.flushInput()
                    self._send_at_command(ser, 'n')
                    logger.info(f"Continuing to flash model: {model.id}")

                    # Send preamble - xmodem library handles handshake
                    await self._report_progress(
                        progress_callback, "flash", progress_base,
                        f"[{idx + 1}/{total_models}] Sending preamble @ {model.flash_address}..."
                    )

                    # Generate preamble packet with flash address
                    preamble = self._generate_preamble(
                        model.flash_address, model.offset, packet_size
                    )
                    logger.info(f"Sending preamble for {model.id} at {model.flash_address}")
                    logger.info(f"Preamble bytes: {preamble[:20].hex()}...")

                    import os
                    import tempfile
                    preamble_file = os.path.join(tempfile.gettempdir(), f"_temp_model_{idx}_preamble.bin")
                    with open(preamble_file, 'wb') as f:
                        f.write(preamble)

                    # Run blocking xmodem in thread to allow WebSocket updates
                    def send_preamble():
                        with open(preamble_file, 'rb') as stream:
                            return modem.send(stream, retry=16)

                    if not await asyncio.to_thread(send_preamble):
                        logger.error(f"Failed to send preamble for model {model.id}")
                        await self._report_progress(
                            progress_callback, "flash", progress_base,
                            "Failed to send preamble"
                        )
                        ser.close()
                        return False

                    # Small delay for device to process preamble
                    logger.debug("Preamble sent, waiting for device response...")
                    await asyncio.sleep(0.5)

                    # Debug: check if there's any data waiting
                    if ser.in_waiting:
                        logger.debug(f"Data waiting after preamble: {ser.in_waiting} bytes")

                    # Wait for reboot prompt again
                    await self._report_progress(
                        progress_callback, "flash", progress_base,
                        f"[{idx + 1}/{total_models}] Preamble sent, waiting..."
                    )
                    if not await self._wait_for_reboot_prompt(ser, timeout=60):
                        logger.error(f"Timeout waiting for reboot prompt after preamble for model {model.id}")
                        await self._report_progress(
                            progress_callback, "flash", progress_base,
                            "Timeout after preamble"
                        )
                        ser.close()
                        return False

                    # Send 'n' to continue - matching official script
                    await asyncio.sleep(1)
                    ser.flushInput()
                    self._send_at_command(ser, 'n')

                    # Send model file - xmodem library handles handshake
                    await self._report_progress(
                        progress_callback, "flash", progress_base,
                        f"[{idx + 1}/{total_models}] Sending model file..."
                    )

                    logger.info(f"Sending model file: {model_path}")

                    # Run blocking xmodem in thread to allow WebSocket updates
                    def send_model():
                        with open(model_path, "rb") as f:
                            return modem.send(f, retry=16, quiet=True)

                    if not await asyncio.to_thread(send_model):
                        logger.error(f"Failed to send model {model.id}")
                        await self._report_progress(
                            progress_callback, "flash", progress_base,
                            "Failed to send model file"
                        )
                        ser.close()
                        return False

                    logger.info(f"Model {model.id} transfer complete")

            # Step 6: Send 'y' to reboot after all models - matching official script
            if await self._wait_for_reboot_prompt(ser, timeout=60):
                self._send_at_command(ser, 'y')
                logger.info("Sent reboot confirmation")

            ser.close()

            await self._report_progress(
                progress_callback, "flash", 100, "Flash complete!"
            )

            return True

        except ImportError:
            logger.error("xmodem library not installed")
            await self._report_progress(
                progress_callback, "flash", 0, "xmodem library not installed"
            )
            return False
        except FileNotFoundError as e:
            logger.error(f"Model file not found: {e}")
            await self._report_progress(
                progress_callback, "flash", 0, f"Model file not found: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Multi-model flash failed: {e}")
            return False
        finally:
            # Always release ESP32 from reset
            if esp32_serial:
                self._release_esp32_reset(esp32_serial)
                logger.info("ESP32 released from reset")
