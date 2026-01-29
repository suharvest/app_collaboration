"""
ESP32 firmware flashing deployer using esptool
"""

import asyncio
import io
import logging
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """Check if running as frozen executable (PyInstaller).

    This must be a function, not a module-level variable, because when uvicorn
    imports the module in a worker process, sys.frozen may not be set yet.
    """
    return getattr(sys, 'frozen', False)


class ESP32Deployer(BaseDeployer):
    """ESP32 firmware flashing via esptool"""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        port = connection.get("port")
        if not port:
            raise ValueError("No port specified for ESP32 device")

        if not config.firmware:
            raise ValueError("No firmware configuration")

        flash_config = config.firmware.flash_config

        try:
            # Step 0: Wait for port to be available (may be held by Himax deployer or other programs)
            await self._report_progress(
                progress_callback, "detect", 0, "Waiting for port to be available..."
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

            # Step 1: Detect chip with retry logic
            await self._report_progress(
                progress_callback, "detect", 0, "Detecting ESP32 chip..."
            )

            # Try detection with automatic reset first
            detect_result = await self._run_esptool([
                "--port", port,
                "--before", "default_reset",
                "--after", "no_reset",
                "chip_id"
            ])

            if not detect_result["success"]:
                # First attempt failed, prompt user for manual boot mode
                await self._report_progress(
                    progress_callback,
                    "detect",
                    30,
                    "Auto-detect failed. Please enter download mode: Hold BOOT button, press RESET, then release BOOT"
                )

                # Wait a moment for user to enter boot mode
                await asyncio.sleep(3)

                # Retry detection
                detect_result = await self._run_esptool([
                    "--port", port,
                    "--before", "no_reset",
                    "--after", "no_reset",
                    "chip_id"
                ])

            if not detect_result["success"]:
                await self._report_progress(
                    progress_callback,
                    "detect",
                    0,
                    f"Detection failed: {detect_result.get('error', 'Unknown error')}",
                )
                return False

            await self._report_progress(
                progress_callback, "detect", 100, "Device detected successfully"
            )

            # Step 2: Optional erase
            if config.get_step_option("erase", default=False):
                await self._report_progress(
                    progress_callback, "erase", 0, "Erasing flash..."
                )

                erase_result = await self._run_esptool(
                    ["--port", port, "--chip", flash_config.chip, "erase_flash"]
                )

                if not erase_result["success"]:
                    await self._report_progress(
                        progress_callback,
                        "erase",
                        0,
                        f"Erase failed: {erase_result.get('error', 'Unknown error')}",
                    )
                    return False

                await self._report_progress(
                    progress_callback, "erase", 100, "Flash erased"
                )

            # Step 3: Flash firmware
            # Re-check port availability before flashing (may have been grabbed by another process)
            if not await self._wait_for_port_available(
                port,
                timeout=5,
                auto_release=True,
                progress_callback=progress_callback
            ):
                await self._report_progress(
                    progress_callback, "flash", 0,
                    f"Port {port} is busy. Please ensure no other program is using it."
                )
                return False

            await self._report_progress(
                progress_callback, "flash", 0, "Starting firmware flash..."
            )

            # Build flash command
            flash_args = [
                "--port", port,
                "--chip", flash_config.chip,
                "--baud", str(flash_config.baud_rate),
                "write_flash",
                "--flash_mode", flash_config.flash_mode,
                "--flash_freq", flash_config.flash_freq,
                "--flash_size", flash_config.flash_size,
            ]

            # Add partition files
            for partition in flash_config.partitions:
                firmware_path = config.get_asset_path(f"assets/watcher_firmware/{partition.file}")
                if not firmware_path or not Path(firmware_path).exists():
                    # Try relative to base path
                    firmware_path = config.get_asset_path(partition.file)

                if not firmware_path or not Path(firmware_path).exists():
                    await self._report_progress(
                        progress_callback,
                        "flash",
                        0,
                        f"Firmware file not found: {partition.file}",
                    )
                    return False

                flash_args.extend([partition.offset, firmware_path])

            # Run flash with progress parsing
            flash_result = await self._run_esptool_with_progress(
                flash_args,
                lambda p, m: asyncio.create_task(
                    self._report_progress(progress_callback, "flash", p, m)
                )
                if progress_callback
                else None,
            )

            if not flash_result["success"]:
                await self._report_progress(
                    progress_callback,
                    "flash",
                    0,
                    f"Flash failed: {flash_result.get('error', 'Unknown error')}",
                )
                return False

            await self._report_progress(
                progress_callback, "flash", 100, "Firmware flashed successfully"
            )

            # Step 4: Verify
            await self._report_progress(
                progress_callback, "verify", 100, "Deployment complete"
            )

            # Reset device if configured
            if config.post_deployment.reset_device:
                try:
                    await self._run_esptool(["--port", port, "run"])
                except Exception as e:
                    logger.warning(f"Failed to reset device: {e}")

            return True

        except Exception as e:
            logger.exception(f"ESP32 deployment failed: {e}")
            await self._report_progress(
                progress_callback, "flash", 0, f"Deployment failed: {str(e) or type(e).__name__}"
            )
            return False

    def _run_esptool_internal(self, args: list) -> dict:
        """Run esptool using Python API (synchronous, for frozen apps)"""
        # Extract port from args for cleanup
        port = None
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                port = args[i + 1]
                break

        try:
            import esptool
            from esptool.util import FatalError

            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            # esptool.main(argv) uses argv directly (not sys.argv format)
            # Do NOT prepend 'esptool.py' - esptool will treat it as a subcommand
            full_args = args

            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    esptool.main(full_args)

                return {
                    "success": True,
                    "stdout": stdout_capture.getvalue(),
                    "stderr": stderr_capture.getvalue(),
                    "error": None,
                }
            except SystemExit as e:
                # esptool calls sys.exit() on completion
                stdout_val = stdout_capture.getvalue()
                stderr_val = stderr_capture.getvalue()

                if e.code == 0:
                    return {
                        "success": True,
                        "stdout": stdout_val,
                        "stderr": stderr_val,
                        "error": None,
                    }
                else:
                    # esptool outputs most errors to stdout, not stderr
                    error_msg = stderr_val.strip() if stderr_val.strip() else self._extract_esptool_error(stdout_val)
                    if not error_msg:
                        error_msg = f"esptool exited with code {e.code}"
                    return {
                        "success": False,
                        "stdout": stdout_val,
                        "stderr": stderr_val,
                        "error": error_msg,
                    }
            except FatalError as e:
                # esptool FatalError (connection failed, etc.)
                stdout_val = stdout_capture.getvalue()
                stderr_val = stderr_capture.getvalue()
                return {
                    "success": False,
                    "stdout": stdout_val,
                    "stderr": stderr_val,
                    "error": str(e),
                }
            finally:
                # Ensure serial port is released after esptool operation
                # esptool may leave port open on connection failure
                if port:
                    self._cleanup_serial_port(port)

        except ImportError as e:
            return {"success": False, "error": f"esptool module not available: {str(e)}"}
        except Exception as e:
            logger.exception("Unexpected error in esptool")
            if port:
                self._cleanup_serial_port(port)
            return {"success": False, "error": str(e)}

    async def _wait_for_port_available(
        self,
        port: str,
        timeout: int = 10,
        auto_release: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Wait for serial port to become available, optionally auto-releasing occupied ports.

        This is needed when:
        - Himax deployer has just released the ESP32 port
        - Another program (Arduino IDE, screen, etc.) is using the port

        Args:
            port: Serial port path
            timeout: Seconds to wait for port availability
            auto_release: If True, automatically terminate processes using the port
            progress_callback: Optional callback for progress updates
        """
        import time

        try:
            import serial
        except ImportError:
            logger.warning("pyserial not available, skipping port availability check")
            return True

        # Lazy import to avoid circular dependency
        from ..services.serial_port_manager import SerialPortManager

        start_time = time.time()
        attempt = 0
        checked_processes = False  # Only check processes once if port is busy

        while (time.time() - start_time) < timeout:
            attempt += 1

            # FIRST: Try to open the port to verify it's available (fast check)
            try:
                ser = serial.Serial()
                ser.port = port
                ser.baudrate = 115200
                ser.timeout = 0.1
                ser.exclusive = True  # Request exclusive access
                ser.open()
                ser.close()
                logger.info(f"Port {port} is available (attempt {attempt})")
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

                if not is_busy:
                    # Other error (port doesn't exist, etc.)
                    logger.warning(f"Port {port} error: {e}")
                    return False

                # Port is busy - check processes only once (slow on Windows)
                if auto_release and not checked_processes:
                    checked_processes = True
                    proc_info = await SerialPortManager.get_process_using_port_async(port)

                    if proc_info:
                        logger.info(
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
                            logger.info(f"Port {port} released successfully")
                            if progress_callback:
                                await self._report_progress(
                                    progress_callback, "detect", 0,
                                    f"Port {port} released successfully"
                                )
                            # Wait a moment for OS to fully release the port
                            await asyncio.sleep(1.0)
                            continue

                logger.debug(f"Port {port} busy, waiting... (attempt {attempt})")
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Unexpected error checking port {port}: {e}")
                return False

        logger.warning(f"Timeout waiting for port {port} to become available")
        return False

    def _extract_esptool_error(self, output: str) -> str:
        """Extract error message from esptool output.

        esptool outputs errors to stdout with patterns like:
        - "A fatal error occurred: Failed to connect to ESP32-S3: No serial data received."
        - "Fatal error: ..."
        """
        if not output:
            return "Unknown error"

        # Look for fatal error patterns
        for line in output.split('\n'):
            line = line.strip()
            if 'fatal error' in line.lower():
                # Extract the error message after the colon
                if ':' in line:
                    return line.split(':', 1)[-1].strip()
                return line
            if 'error' in line.lower() and ('failed' in line.lower() or 'cannot' in line.lower()):
                return line

        # Return last non-empty lines as context
        lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
        if lines:
            return lines[-1][:200]  # Last line, truncated

        return "Unknown error"

    def _cleanup_serial_port(self, port: str):
        """Force close serial port if it was left open by esptool

        On Windows, serial ports may not be released immediately after a process
        exits, so we retry with exponential backoff.
        """
        import time

        try:
            import serial
        except ImportError:
            logger.debug("pyserial not available for port cleanup")
            return

        # Retry settings - more attempts on Windows where port release is slower
        max_retries = 5 if sys.platform == "win32" else 2
        base_delay = 0.2  # 200ms initial delay

        for attempt in range(max_retries):
            try:
                # Try to open and immediately close to release any locks
                ser = serial.Serial()
                ser.port = port
                ser.baudrate = 115200
                ser.timeout = 0.1

                ser.open()
                ser.close()
                logger.debug(f"Serial port {port} cleaned up successfully")
                return
            except serial.SerialException as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 200ms, 400ms, 800ms, 1600ms, 3200ms
                    delay = base_delay * (2 ** attempt)
                    logger.debug(
                        f"Serial port {port} busy, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(delay)
                else:
                    # Final attempt failed - port might already be closed or
                    # held by another process, which is acceptable
                    logger.debug(
                        f"Serial port {port} cleanup failed after {max_retries} "
                        f"attempts: {e}"
                    )
            except Exception as e:
                logger.debug(f"Unexpected error during serial port cleanup for {port}: {e}")
                return

    async def _run_esptool(self, args: list) -> dict:
        """Run esptool command"""
        frozen = is_frozen()
        logger.info(f"Running esptool, frozen={frozen}, sys.frozen={getattr(sys, 'frozen', 'NOT_SET')}")

        # For frozen apps OR Windows, use Python API directly
        # Windows has issues with asyncio subprocess for esptool
        if frozen or sys.platform == "win32":
            logger.info(f"Using Python API for esptool (frozen={frozen}, platform={sys.platform})")
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._run_esptool_internal, args)

        # For development on macOS/Linux, use subprocess
        logger.info("Using subprocess for esptool (development mode)")

        # Use sys.executable to get the current Python interpreter path
        current_python = sys.executable

        commands_to_try = [
            ["esptool.py"] + args,
            [current_python, "-m", "esptool"] + args,
            ["python", "-m", "esptool"] + args,
            ["python3", "-m", "esptool"] + args,
        ]

        last_error = None
        for cmd in commands_to_try:
            try:
                logger.info(f"Trying esptool command: {cmd[0]}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

                logger.info(f"esptool returncode: {process.returncode}")
                logger.info(f"esptool stdout: {stdout_str[:500] if stdout_str else '(empty)'}")
                logger.info(f"esptool stderr: {stderr_str[:500] if stderr_str else '(empty)'}")

                # esptool outputs most errors to stdout, not stderr
                # Extract error message from stdout if stderr is empty
                error_msg = None
                if process.returncode != 0:
                    error_msg = stderr_str if stderr_str.strip() else self._extract_esptool_error(stdout_str)
                    logger.info(f"esptool error_msg: {error_msg}")

                return {
                    "success": process.returncode == 0,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "error": error_msg,
                }

            except FileNotFoundError as e:
                logger.debug(f"Command {cmd[0]} not found: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.debug(f"Command {cmd[0]} failed: {e}")
                last_error = e
                continue

        # All subprocess attempts failed, fall back to Python API
        logger.info(f"All subprocess commands failed, falling back to esptool Python API. Last error: {last_error}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run_esptool_internal, args)

    def _run_esptool_with_progress_internal(
        self, args: list, output_lines: list
    ) -> dict:
        """Run esptool with output capture for progress parsing (synchronous)"""
        # Extract port from args for cleanup
        port = None
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                port = args[i + 1]
                break

        try:
            import esptool
            from esptool.util import FatalError

            class LineCapture(io.StringIO):
                """StringIO that also appends lines to a list"""
                def __init__(self, lines_list):
                    super().__init__()
                    self.lines_list = lines_list

                def write(self, s):
                    super().write(s)
                    # Split by newlines and add non-empty lines
                    for line in s.split('\n'):
                        line = line.strip()
                        if line:
                            self.lines_list.append(line)
                    return len(s)

            stdout_capture = LineCapture(output_lines)
            stderr_capture = LineCapture(output_lines)

            # esptool.main(argv) uses argv directly (not sys.argv format)
            # Do NOT prepend 'esptool.py' - esptool will treat it as a subcommand
            full_args = args

            try:
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    esptool.main(full_args)
                return {"success": True}
            except SystemExit as e:
                if e.code == 0:
                    return {"success": True}
                else:
                    error_context = "\n".join(output_lines[-5:]) if output_lines else "Unknown error"
                    return {"success": False, "error": error_context}
            except FatalError as e:
                # esptool FatalError (connection failed, etc.)
                error_context = "\n".join(output_lines[-5:]) if output_lines else str(e)
                return {"success": False, "error": error_context}
            finally:
                # Ensure serial port is released after esptool operation
                if port:
                    self._cleanup_serial_port(port)

        except ImportError as e:
            return {"success": False, "error": f"esptool module not available: {str(e)}"}
        except Exception as e:
            logger.exception("Unexpected error in esptool with progress")
            if port:
                self._cleanup_serial_port(port)
            return {"success": False, "error": str(e)}

    async def _run_esptool_with_progress(
        self, args: list, progress_callback: Optional[Callable]
    ) -> dict:
        """Run esptool with real-time progress parsing"""

        # For frozen apps OR Windows, use Python API with polling
        # Windows has issues with asyncio subprocess for esptool
        if is_frozen() or sys.platform == "win32":
            import concurrent.futures

            logger.info(f"Using Python API for esptool with progress (frozen={is_frozen()}, platform={sys.platform})")

            output_lines = []
            last_progress = 0

            loop = asyncio.get_event_loop()
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

            future = loop.run_in_executor(
                executor,
                self._run_esptool_with_progress_internal,
                args,
                output_lines
            )

            # Poll for progress while esptool runs
            processed_lines = 0
            while not future.done():
                await asyncio.sleep(0.1)

                # Process new output lines
                while processed_lines < len(output_lines):
                    line_str = output_lines[processed_lines]
                    processed_lines += 1

                    logger.debug(f"esptool: {line_str}")

                    # Parse progress
                    if "Writing at" in line_str and "%" in line_str:
                        match = re.search(r"\((\d+)\s*%\)", line_str)
                        if match and progress_callback:
                            progress = int(match.group(1))
                            if progress >= last_progress + 5 or progress == 100:
                                progress_callback(progress, f"Flashing... {progress}%")
                                last_progress = progress
                    elif progress_callback and line_str and not line_str.startswith(".."):
                        progress_callback(last_progress, line_str)

            # Process any remaining lines
            while processed_lines < len(output_lines):
                line_str = output_lines[processed_lines]
                processed_lines += 1
                logger.debug(f"esptool: {line_str}")

                if "Writing at" in line_str and "%" in line_str:
                    match = re.search(r"\((\d+)\s*%\)", line_str)
                    if match and progress_callback:
                        progress = int(match.group(1))
                        progress_callback(progress, f"Flashing... {progress}%")

            executor.shutdown(wait=False)
            return await future

        # For development on macOS/Linux, use subprocess with streaming
        # Use sys.executable to get the current Python interpreter path
        current_python = sys.executable

        commands_to_try = [
            ["esptool.py"] + args,
            [current_python, "-m", "esptool"] + args,
            ["python", "-m", "esptool"] + args,
            ["python3", "-m", "esptool"] + args,
        ]

        process = None
        for cmd in commands_to_try:
            try:
                logger.info(f"Trying esptool command (with progress): {cmd[0]}")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                break  # Success, exit loop
            except FileNotFoundError:
                logger.debug(f"Command {cmd[0]} not found")
                continue

        if process is None:
            # All subprocess attempts failed, fall back to Python API
            logger.info("Falling back to esptool Python API for progress")
            output_lines = []
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._run_esptool_with_progress_internal,
                args,
                output_lines
            )

        try:

            last_progress = 0
            all_output = []

            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                line_str = line.decode().strip()
                if not line_str:
                    continue

                all_output.append(line_str)
                logger.debug(f"esptool: {line_str}")

                # Parse progress from esptool output
                # Example: "Writing at 0x00010000... (5 %)"
                if "Writing at" in line_str and "%" in line_str:
                    match = re.search(r"\((\d+)\s*%\)", line_str)
                    if match and progress_callback:
                        progress = int(match.group(1))
                        # Report every 5% for more granular updates
                        if progress >= last_progress + 5 or progress == 100:
                            progress_callback(progress, f"Flashing... {progress}%")
                            last_progress = progress

                # Send all meaningful status messages
                elif progress_callback:
                    # Skip empty lines and pure dots
                    if line_str and not line_str.startswith(".."):
                        progress_callback(last_progress, line_str)

            await process.wait()

            if process.returncode != 0:
                # Return last few lines as error context
                error_context = "\n".join(all_output[-5:]) if all_output else "Unknown error"
                return {"success": False, "error": error_context}

            return {"success": process.returncode == 0}

        except Exception as e:
            return {"success": False, "error": str(e)}
