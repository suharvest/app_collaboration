"""
Serial port process manager for detecting and releasing occupied ports.

Cross-platform support for Linux, macOS, and Windows using psutil and lsof.
"""

import logging
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

# Known serial port applications that can be safely terminated
KNOWN_SERIAL_APPS = [
    # IDEs
    "arduino", "arduino-cli", "platformio", "platformio-core",
    # Terminal tools
    "screen", "minicom", "picocom", "cu", "tip",
    # Flashing tools
    "esptool", "esptool.py", "avrdude", "openocd", "stm32flash",
    # Serial monitors
    "putty", "tera_term", "teraterm", "coolterm", "serial_monitor",
    "esp_idf_monitor", "idf_monitor", "idf.py",
    # Python scripts (common for serial work)
    "python", "python3", "python.exe",
]


class SerialPortManager:
    """Cross-platform serial port process management using psutil and lsof"""

    @staticmethod
    def get_process_using_port(port: str) -> Optional[Dict[str, Any]]:
        """Detect the process using a serial port.

        Args:
            port: Serial port path (e.g., /dev/ttyUSB0, COM3)

        Returns:
            Dict with process info (pid, name, cmdline) or None if not found
        """
        # On macOS/Linux, use lsof which is more reliable for character devices
        if sys.platform in ("darwin", "linux"):
            result = SerialPortManager._get_process_using_port_lsof(port)
            if result:
                return result

        # Fallback to psutil (works better on Windows)
        return SerialPortManager._get_process_using_port_psutil(port)

    @staticmethod
    def _get_process_using_port_lsof(port: str) -> Optional[Dict[str, Any]]:
        """Use lsof to detect process using serial port (macOS/Linux)."""
        port_variants = SerialPortManager._get_port_variants(port)

        for variant in port_variants:
            try:
                # lsof -t returns just the PID
                result = subprocess.run(
                    ["lsof", "-t", variant],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    pid = int(result.stdout.strip().split()[0])
                    try:
                        proc = psutil.Process(pid)
                        return {
                            'pid': pid,
                            'name': proc.name(),
                            'cmdline': ' '.join(proc.cmdline() or [])
                        }
                    except psutil.NoSuchProcess:
                        continue
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError) as e:
                logger.debug(f"lsof check failed for {variant}: {e}")
                continue

        return None

    @staticmethod
    def _get_process_using_port_psutil(port: str) -> Optional[Dict[str, Any]]:
        """Use psutil to detect process using serial port."""
        port_variants = SerialPortManager._get_port_variants(port)

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check open files
                try:
                    for f in proc.open_files():
                        if any(variant in f.path for variant in port_variants):
                            return {
                                'pid': proc.pid,
                                'name': proc.name(),
                                'cmdline': ' '.join(proc.cmdline() or [])
                            }
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    pass

                # Windows: check command line for COM port references
                if sys.platform == "win32":
                    cmdline = proc.cmdline()
                    if cmdline:
                        cmdline_str = ' '.join(cmdline).lower()
                        for variant in port_variants:
                            if variant.lower() in cmdline_str:
                                proc_name_lower = proc.name().lower()
                                if any(app in proc_name_lower for app in KNOWN_SERIAL_APPS):
                                    return {
                                        'pid': proc.pid,
                                        'name': proc.name(),
                                        'cmdline': cmdline_str
                                    }

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return None

    @staticmethod
    def _get_port_variants(port: str) -> List[str]:
        """Get port name variants for matching.

        On macOS, /dev/cu.* and /dev/tty.* refer to the same port.
        """
        variants = [port]

        if sys.platform == "darwin":
            if "/dev/cu." in port:
                variants.append(port.replace("/dev/cu.", "/dev/tty."))
            elif "/dev/tty." in port:
                variants.append(port.replace("/dev/tty.", "/dev/cu."))

        return variants

    @staticmethod
    def release_port(port: str, timeout: int = 3) -> bool:
        """Release a serial port by terminating the occupying process.

        Since we use lsof to confirm the process is actually using the port,
        we can safely terminate it - the user explicitly wants to deploy to this port.

        Args:
            port: Serial port path
            timeout: Seconds to wait for graceful termination before SIGKILL

        Returns:
            True if port was released or wasn't occupied, False on failure
        """
        proc_info = SerialPortManager.get_process_using_port(port)

        if not proc_info:
            logger.debug(f"Port {port} is not occupied by any detected process")
            return True

        try:
            proc = psutil.Process(proc_info['pid'])
            proc_name = proc_info['name']
            proc_pid = proc_info['pid']
            proc_cmdline = proc_info.get('cmdline', '')

            # Log what we're terminating for debugging
            logger.info(
                f"Terminating process to release {port}: "
                f"{proc_name} (PID: {proc_pid})"
            )
            if proc_cmdline:
                # Show abbreviated cmdline
                cmdline_short = proc_cmdline[:100] + ('...' if len(proc_cmdline) > 100 else '')
                logger.debug(f"Process cmdline: {cmdline_short}")

            # Try graceful termination first (SIGTERM on Unix)
            proc.terminate()

            try:
                proc.wait(timeout=timeout)
                logger.info(f"Process {proc_name} (PID: {proc_pid}) terminated gracefully")
            except psutil.TimeoutExpired:
                # Force kill (SIGKILL on Unix)
                logger.warning(f"Process {proc_name} did not exit, force killing...")
                proc.kill()
                try:
                    proc.wait(timeout=1)
                    logger.info(f"Process {proc_name} (PID: {proc_pid}) killed")
                except psutil.TimeoutExpired:
                    logger.error(f"Failed to kill process {proc_name} (PID: {proc_pid})")
                    return False

            # Wait a moment for OS to release the port
            time.sleep(0.5)
            return True

        except psutil.NoSuchProcess:
            # Process already exited
            logger.debug(f"Process {proc_info['pid']} already exited")
            return True
        except psutil.AccessDenied:
            logger.error(
                f"Permission denied to terminate {proc_info['name']} (PID: {proc_info['pid']}). "
                f"Try running with elevated privileges."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to release port {port}: {e}")
            return False

    @staticmethod
    def scan_known_serial_processes() -> List[Dict[str, Any]]:
        """Scan for running processes that are known serial tools.

        Useful for Windows where open_files() may not detect COM ports.

        Returns:
            List of process info dicts for known serial apps
        """
        results = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                proc_name_lower = proc.name().lower()
                if any(app in proc_name_lower for app in KNOWN_SERIAL_APPS):
                    results.append({
                        'pid': proc.pid,
                        'name': proc.name(),
                        'cmdline': ' '.join(proc.cmdline() or [])
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return results

    @staticmethod
    async def release_port_async(port: str, timeout: int = 3) -> bool:
        """Async wrapper for release_port.

        Runs the blocking release_port in a thread executor.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, SerialPortManager.release_port, port, timeout)

    @staticmethod
    async def get_process_using_port_async(port: str) -> Optional[Dict[str, Any]]:
        """Async wrapper for get_process_using_port.

        Runs the blocking get_process_using_port in a thread executor.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, SerialPortManager.get_process_using_port, port)
