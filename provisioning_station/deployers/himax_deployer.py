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
from typing import Callable, Optional, Dict, Any, List

import serial
import serial.tools.list_ports

from .base import BaseDeployer
from ..models.device import DeviceConfig, HimaxModelConfig

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
                progress_callback, "wait_reset", 100, "Ready for flashing"
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

        IMPORTANT: SenseCAP Watcher exposes two serial ports with the same VID/PID:
        - usbmodem* for Himax WE2 (what we want)
        - wchusbserial* for ESP32-S3 (NOT what we want)

        We must prioritize usbmodem ports over wchusbserial ports.
        """
        detection = config.detection if hasattr(config, 'detection') else None

        patterns = self.DEFAULT_PORT_PATTERNS
        if detection and hasattr(detection, 'fallback_ports') and detection.fallback_ports:
            patterns = detection.fallback_ports + patterns

        # Method 1: Look for usbmodem ports first (Himax WE2 uses usbmodem)
        for port in serial.tools.list_ports.comports():
            if 'usbmodem' in port.device.lower():
                for pattern in patterns:
                    if fnmatch.fnmatch(port.device, pattern):
                        logger.info(f"Found Himax device by usbmodem pattern: {port.device}")
                        return port.device

        # Method 2: Check fallback patterns (excluding wchusbserial which is ESP32)
        for port in serial.tools.list_ports.comports():
            if 'wchusbserial' in port.device.lower():
                continue
            for pattern in patterns:
                if fnmatch.fnmatch(port.device, pattern):
                    logger.info(f"Found Himax device by pattern: {port.device}")
                    return port.device

        # Method 3: VID/PID matching (only for usbmodem ports)
        vid = self.DEFAULT_VID
        pid = self.DEFAULT_PID
        if detection:
            vid_str = getattr(detection, 'usb_vendor_id', None)
            pid_str = getattr(detection, 'usb_product_id', None)
            if vid_str:
                vid = int(vid_str, 16) if vid_str.startswith('0x') else int(vid_str)
            if pid_str:
                pid = int(pid_str, 16) if pid_str.startswith('0x') else int(pid_str)

        for port in serial.tools.list_ports.comports():
            if port.vid == vid and port.pid == pid:
                if 'wchusbserial' in port.device.lower():
                    continue
                logger.info(f"Found Himax device by VID/PID: {port.device}")
                return port.device

        return None

    def _verify_port_exists(self, port: str) -> bool:
        """Verify the port exists"""
        for p in serial.tools.list_ports.comports():
            if p.device == port:
                return True
        return False

    def _find_companion_esp32_port(self, himax_port: str) -> Optional[str]:
        """Find the companion ESP32 serial port for SenseCAP Watcher."""
        logger.debug(f"Looking for companion ESP32 port for Himax: {himax_port}")

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

    async def _flash_with_xmodem(
        self,
        port: str,
        firmware_path: str,
        baudrate: int,
        progress_callback: Optional[Callable],
        esp32_port: Optional[str] = None,
    ) -> bool:
        """Flash using xmodem protocol with proper Himax bootloader handshake

        Protocol:
        1. Hold ESP32 in reset (if SenseCAP Watcher)
        2. Open serial port and send "1" repeatedly to trigger bootloader menu
        3. Wait for "Xmodem download and burn FW image"
        4. Wait for "C" character (xmodem-CRC ready)
        5. Transfer firmware using xmodem
        6. Wait for reboot prompt and send "y"
        7. Release ESP32 from reset
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

            # Step 1: Open Himax serial port
            await self._report_progress(
                progress_callback, "flash", 10, "Connecting to Himax..."
            )

            ser = serial.Serial(port, baudrate=baudrate, timeout=0.01)
            logger.info(f"Opened Himax port: {port}")

            # Step 2: Wait for bootloader and send "1" to select xmodem download
            await self._report_progress(
                progress_callback, "flash", 15, "Waiting for bootloader (press RESET)..."
            )

            rbuf = b""
            timeout = 30000  # 30 seconds
            bootloader_ready = False

            while timeout > 0:
                ser.write(b"1")
                rbuf += ser.read(128)

                if b"Xmodem download and burn FW image" in rbuf:
                    ser.write(b"1")
                    bootloader_ready = True
                    logger.info("Bootloader ready, xmodem mode selected")
                    break

                # Trim buffer to prevent memory issues
                if len(rbuf) > 4096:
                    rbuf = rbuf[-2048:]

                timeout -= 10
                await asyncio.sleep(0.01)

            if not bootloader_ready:
                logger.error("Timeout waiting for bootloader")
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 30, "Bootloader ready"
            )

            # Step 3: Wait for "C" character (xmodem-CRC ready signal)
            timeout = 5000  # 5 seconds
            xmodem_ready = False

            while timeout > 0:
                c = ser.read(1)
                if c == b"C":
                    xmodem_ready = True
                    # Wait for bootloader to finish outputting debug text
                    await asyncio.sleep(0.5)
                    # Drain any remaining output in buffer
                    while ser.in_waiting:
                        drained = ser.read(ser.in_waiting)
                        logger.debug(f"Drained buffer: {drained[:50]}...")
                        await asyncio.sleep(0.1)
                    break
                timeout -= 10
                await asyncio.sleep(0.01)

            if not xmodem_ready:
                logger.error("Timeout waiting for xmodem ready signal")
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 40, "Starting transfer..."
            )

            # Step 4: Transfer firmware using xmodem
            ser.timeout = 2  # Longer timeout for xmodem transfer
            ser.reset_input_buffer()  # Clear any remaining data
            ser.reset_output_buffer()

            from xmodem import XMODEM

            def getc(size, timeout=1):
                return ser.read(size) or None

            def putc(data, timeout=1):
                return ser.write(data) or None

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
            rbuf = b""
            ser.timeout = 0.01
            timeout = 10000  # 10 seconds

            while timeout > 0:
                rbuf += ser.read(128)
                if b"Do you want to end file transmission and reboot" in rbuf:
                    ser.write(b"y")
                    logger.info("Sent reboot confirmation")
                    break
                timeout -= 10
                await asyncio.sleep(0.01)

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
        timeout: int = 30
    ) -> bool:
        """Wait for the reboot confirmation prompt from bootloader"""
        rbuf = b""
        start = time.time()

        while (time.time() - start) < timeout:
            rbuf += ser.read(256)
            if b"Do you want to end file transmission and reboot" in rbuf:
                return True
            # Trim buffer to prevent memory issues
            if len(rbuf) > 4096:
                rbuf = rbuf[-2048:]
            await asyncio.sleep(0.01)

        return False

    async def _wait_for_bootloader(
        self,
        ser: serial.Serial,
        timeout: int = 30
    ) -> bool:
        """Wait for bootloader and enter xmodem download mode"""
        rbuf = b""
        timeout_ms = timeout * 1000

        while timeout_ms > 0:
            ser.write(b"1")
            rbuf += ser.read(128)

            if b"Xmodem download and burn FW image" in rbuf:
                ser.write(b"1")
                logger.info("Bootloader ready, xmodem mode selected")
                return True

            # Trim buffer to prevent memory issues
            if len(rbuf) > 4096:
                rbuf = rbuf[-2048:]

            timeout_ms -= 10
            await asyncio.sleep(0.01)

        logger.error("Timeout waiting for bootloader")
        return False

    async def _wait_for_xmodem_ready(
        self,
        ser: serial.Serial,
        timeout: int = 5
    ) -> bool:
        """Wait for 'C' character indicating xmodem-CRC ready"""
        timeout_ms = timeout * 1000

        while timeout_ms > 0:
            c = ser.read(1)
            if c == b"C":
                # Wait for bootloader to finish outputting debug text
                await asyncio.sleep(0.5)
                # Drain any remaining output
                while ser.in_waiting:
                    ser.read(ser.in_waiting)
                    await asyncio.sleep(0.1)
                return True
            timeout_ms -= 10
            await asyncio.sleep(0.01)

        logger.error("Timeout waiting for xmodem ready signal")
        return False

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

        Protocol flow:
        1. Enter bootloader (send '1', wait for xmodem prompt)
        2. Send base firmware via xmodem
        3. For each model:
           a. Wait for reboot prompt, send 'n' to continue
           b. Send preamble packet with flash address
           c. Wait for reboot prompt, send 'n'
           d. Send model file via xmodem
        4. After all models, send 'y' to reboot
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

            # Step 1: Open Himax serial port
            await self._report_progress(
                progress_callback, "flash", 10, "Connecting to Himax..."
            )

            ser = serial.Serial(port, baudrate=baudrate, timeout=0.01)
            logger.info(f"Opened Himax port: {port}")

            # Step 2: Wait for bootloader
            await self._report_progress(
                progress_callback, "flash", 15, "Waiting for bootloader (press RESET)..."
            )

            if not await self._wait_for_bootloader(ser, timeout=30):
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 20, "Bootloader ready"
            )

            # Step 3: Wait for xmodem ready signal ('C')
            if not await self._wait_for_xmodem_ready(ser, timeout=5):
                ser.close()
                return False

            await self._report_progress(
                progress_callback, "flash", 25, "Starting base firmware transfer..."
            )

            # Step 4: Transfer base firmware using xmodem
            ser.timeout = 2
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            from xmodem import XMODEM

            def getc(size, timeout=1):
                return ser.read(size) or None

            def putc(data, timeout=1):
                return ser.write(data) or None

            modem = XMODEM(getc, putc, mode=protocol)

            with open(firmware_path, "rb") as f:
                if not modem.send(f, retry=16, quiet=True):
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

                    # Wait for reboot prompt
                    ser.timeout = 0.1
                    if not await self._wait_for_reboot_prompt(ser, timeout=30):
                        logger.error(f"Timeout waiting for reboot prompt before model {model.id}")
                        ser.close()
                        return False

                    # Send 'n' to continue (not reboot)
                    ser.write(b'n')
                    logger.info(f"Continuing to flash model: {model.id}")
                    await asyncio.sleep(1)
                    ser.reset_input_buffer()

                    # Wait for xmodem ready and send preamble
                    if not await self._wait_for_xmodem_ready(ser, timeout=5):
                        logger.error("Timeout waiting for xmodem ready before preamble")
                        ser.close()
                        return False

                    ser.timeout = 2
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    # Send preamble packet with flash address
                    preamble = self._generate_preamble(
                        model.flash_address, model.offset, packet_size
                    )
                    logger.info(f"Sending preamble for {model.id} at {model.flash_address}")

                    import io
                    preamble_stream = io.BytesIO(preamble)
                    if not modem.send(preamble_stream, retry=16, quiet=True):
                        logger.error(f"Failed to send preamble for model {model.id}")
                        ser.close()
                        return False

                    # Wait for reboot prompt again
                    ser.timeout = 0.1
                    if not await self._wait_for_reboot_prompt(ser, timeout=30):
                        logger.error(f"Timeout waiting for reboot prompt after preamble for model {model.id}")
                        ser.close()
                        return False

                    # Send 'n' to continue
                    ser.write(b'n')
                    await asyncio.sleep(1)
                    ser.reset_input_buffer()

                    # Wait for xmodem ready and send model file
                    if not await self._wait_for_xmodem_ready(ser, timeout=5):
                        logger.error(f"Timeout waiting for xmodem ready before model {model.id}")
                        ser.close()
                        return False

                    ser.timeout = 2
                    ser.reset_input_buffer()
                    ser.reset_output_buffer()

                    # Send model file
                    model_path = self._resolve_model_path(model, base_path)
                    logger.info(f"Sending model file: {model_path}")

                    with open(model_path, "rb") as f:
                        if not modem.send(f, retry=16, quiet=True):
                            logger.error(f"Failed to send model {model.id}")
                            ser.close()
                            return False

                    logger.info(f"Model {model.id} transfer complete")

            # Step 6: Send 'y' to reboot after all models
            ser.timeout = 0.1
            if await self._wait_for_reboot_prompt(ser, timeout=30):
                ser.write(b'y')
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
