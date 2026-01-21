"""
ESP32 firmware flashing deployer using esptool
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Callable, Optional, Dict, Any

from .base import BaseDeployer
from ..models.device import DeviceConfig

logger = logging.getLogger(__name__)


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
            # Step 1: Detect chip
            await self._report_progress(
                progress_callback, "detect", 0, "Detecting ESP32 chip..."
            )

            detect_result = await self._run_esptool(["--port", port, "chip_id"])

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
            logger.error(f"ESP32 deployment failed: {e}")
            await self._report_progress(
                progress_callback, "flash", 0, f"Deployment failed: {str(e)}"
            )
            return False

    async def _run_esptool(self, args: list) -> dict:
        """Run esptool command"""
        try:
            cmd = ["esptool.py"] + args
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            return {
                "success": process.returncode == 0,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "error": stderr.decode() if process.returncode != 0 else None,
            }

        except FileNotFoundError:
            # Try with python -m
            try:
                cmd = ["python", "-m", "esptool"] + args
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "error": stderr.decode() if process.returncode != 0 else None,
                }
            except Exception as e:
                return {"success": False, "error": f"esptool not found: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_esptool_with_progress(
        self, args: list, progress_callback: Optional[Callable]
    ) -> dict:
        """Run esptool with real-time progress parsing"""
        try:
            cmd = ["esptool.py"] + args
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
            except FileNotFoundError:
                cmd = ["python", "-m", "esptool"] + args
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )

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
                        # Only report every 10% to avoid too many updates
                        if progress >= last_progress + 10 or progress == 100:
                            progress_callback(progress, f"Flashing... {progress}%")
                            last_progress = progress

                # Send important status messages
                elif progress_callback:
                    # Key esptool messages to forward
                    if any(keyword in line_str for keyword in [
                        "Connecting", "Chip is", "Features:", "Crystal is",
                        "MAC:", "Uploading", "Compressed", "Wrote", "Hash",
                        "Leaving", "Hard resetting", "error", "Error", "failed", "Failed"
                    ]):
                        progress_callback(last_progress, line_str)

            await process.wait()

            if process.returncode != 0:
                # Return last few lines as error context
                error_context = "\n".join(all_output[-5:]) if all_output else "Unknown error"
                return {"success": False, "error": error_context}

            return {"success": process.returncode == 0}

        except Exception as e:
            return {"success": False, "error": str(e)}
