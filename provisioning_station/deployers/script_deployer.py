"""
Script deployment deployer - executes local scripts with user configuration
"""

import asyncio
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ..models.device import DeviceConfig
from .action_executor import LocalActionExecutor
from .base import BaseDeployer

logger = logging.getLogger(__name__)


class ScriptDeployer(BaseDeployer):
    """Local script execution deployment"""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        # Get script deployment config - check both 'script' and 'deployment' keys
        script_config = config.script
        if not script_config:
            # Try loading from raw deployment key if not parsed
            raise ValueError("No script deployment configuration found")

        user_inputs = connection.get("user_inputs", {})

        try:
            # Step 1: Validate working directory
            await self._report_progress(
                progress_callback, "validate", 0, "Validating environment..."
            )

            working_dir = self._resolve_working_dir(config, script_config.working_dir)
            if not working_dir.exists():
                await self._report_progress(
                    progress_callback,
                    "validate",
                    0,
                    f"Working directory not found: {working_dir}",
                )
                return False

            await self._report_progress(
                progress_callback, "validate", 100, f"Working directory: {working_dir}"
            )

            # Before actions
            action_executor = LocalActionExecutor()
            if not await self._execute_actions(
                "before", config, connection, progress_callback, action_executor
            ):
                return False

            # Step 2: Execute setup commands
            if script_config.setup_commands:
                await self._report_progress(
                    progress_callback, "setup", 0, "Running setup commands..."
                )

                for i, cmd_config in enumerate(script_config.setup_commands):
                    cmd = self._substitute_variables(cmd_config.command, user_inputs)
                    desc = cmd_config.description or cmd

                    await self._report_progress(
                        progress_callback,
                        "setup",
                        int((i / len(script_config.setup_commands)) * 100),
                        f"Running: {desc}",
                    )

                    success = await self._run_command(cmd, working_dir)
                    if not success:
                        await self._report_progress(
                            progress_callback,
                            "setup",
                            0,
                            f"Setup command failed: {cmd}",
                        )
                        return False

                await self._report_progress(
                    progress_callback, "setup", 100, "Setup completed"
                )

            # Step 3: Generate config file from template
            if script_config.config_template:
                await self._report_progress(
                    progress_callback,
                    "configure",
                    0,
                    "Generating configuration file...",
                )

                template = script_config.config_template
                config_path = working_dir / template.file
                content = self._substitute_variables(template.content, user_inputs)

                try:
                    config_path.parent.mkdir(parents=True, exist_ok=True)
                    config_path.write_text(content)
                    await self._report_progress(
                        progress_callback,
                        "configure",
                        100,
                        f"Configuration written to {template.file}",
                    )
                except Exception as e:
                    await self._report_progress(
                        progress_callback,
                        "configure",
                        0,
                        f"Failed to write config: {e}",
                    )
                    return False

            # Step 4: Execute start command
            if script_config.start_command:
                await self._report_progress(
                    progress_callback, "start", 0, "Starting service..."
                )

                # Select platform-specific command
                start_cmd = script_config.start_command
                if sys.platform == "win32":
                    cmd = start_cmd.windows
                else:
                    cmd = start_cmd.linux_macos

                if not cmd:
                    platform_name = (
                        "Windows" if sys.platform == "win32" else "Linux/macOS"
                    )
                    await self._report_progress(
                        progress_callback,
                        "start",
                        0,
                        f"No start command configured for {platform_name}. "
                        f"Please add 'start_command.{'windows' if sys.platform == 'win32' else 'linux_macos'}' to the solution config.",
                    )
                    return False

                # Build environment variables
                env = os.environ.copy()
                for key, value in start_cmd.env.items():
                    env[key] = self._substitute_variables(value, user_inputs)

                # Start the process
                process = await self._start_process(cmd, working_dir, env)
                if not process:
                    await self._report_progress(
                        progress_callback,
                        "start",
                        0,
                        "Failed to start process",
                    )
                    return False

                await self._report_progress(
                    progress_callback, "start", 50, "Process started"
                )

                # Step 5: Health check
                if script_config.health_check:
                    await self._report_progress(
                        progress_callback,
                        "health_check",
                        0,
                        "Performing health check...",
                    )

                    health_config = script_config.health_check
                    healthy = await self._perform_health_check(
                        process,
                        health_config,
                        progress_callback,
                    )

                    if not healthy:
                        await self._report_progress(
                            progress_callback,
                            "health_check",
                            0,
                            "Health check failed",
                        )
                        # Try to terminate the process
                        try:
                            process.terminate()
                        except Exception:
                            pass
                        return False

                    await self._report_progress(
                        progress_callback, "health_check", 100, "Service is healthy"
                    )
                else:
                    # No health check, just wait a bit
                    await asyncio.sleep(2)

                await self._report_progress(
                    progress_callback, "start", 100, "Service started successfully"
                )

            # After actions
            if not await self._execute_actions(
                "after", config, connection, progress_callback, action_executor
            ):
                return False

            return True

        except Exception as e:
            logger.error(f"Script deployment failed: {e}")
            await self._report_progress(
                progress_callback, "start", 0, f"Deployment failed: {str(e)}"
            )
            return False

    def _resolve_working_dir(
        self, config: DeviceConfig, relative_dir: Optional[str]
    ) -> Path:
        """Resolve working directory path"""
        if relative_dir:
            if config.base_path:
                return Path(config.base_path) / relative_dir
            return Path(relative_dir)
        return Path(config.base_path) if config.base_path else Path.cwd()

    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Substitute {{variable}} placeholders with actual values"""
        result = template
        for key, value in variables.items():
            # Handle both {{key}} and {{ key }} formats
            result = re.sub(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                str(value) if value is not None else "",
                result,
            )
        return result

    async def _run_command(self, cmd: str, working_dir: Path) -> bool:
        """Run a shell command with proper platform handling"""
        try:
            if sys.platform == "win32":
                # On Windows, use PowerShell for better script compatibility
                # PowerShell can handle most bash-like commands and has better Unicode support
                powershell_cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    cmd,
                ]
                process = await asyncio.create_subprocess_exec(
                    *powershell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(working_dir),
                )
            else:
                # On Unix, use explicit shell with proper argument handling
                process = await asyncio.create_subprocess_exec(
                    "/bin/sh",
                    "-c",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(working_dir),
                )

            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                logger.error(f"Command failed: {cmd}")
                logger.error(f"stderr: {stderr.decode('utf-8', errors='replace')}")
                return False
            return True

        except Exception as e:
            logger.error(f"Failed to run command '{cmd}': {e}")
            return False

    async def _start_process(
        self,
        cmd: str,
        working_dir: Path,
        env: Dict[str, str],
    ) -> Optional[asyncio.subprocess.Process]:
        """Start a long-running process with proper platform handling"""
        try:
            if sys.platform == "win32":
                # On Windows, use PowerShell for better compatibility
                # CREATE_NEW_PROCESS_GROUP allows for proper process management
                import subprocess

                powershell_cmd = [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    cmd,
                ]
                process = await asyncio.create_subprocess_exec(
                    *powershell_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(working_dir),
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # On Unix, use explicit shell invocation
                process = await asyncio.create_subprocess_exec(
                    "/bin/sh",
                    "-c",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=str(working_dir),
                    env=env,
                )
            return process

        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            return None

    async def _perform_health_check(
        self,
        process: asyncio.subprocess.Process,
        health_config,
        progress_callback: Optional[Callable],
    ) -> bool:
        """Perform health check based on configuration"""
        if health_config.type == "log_pattern":
            return await self._check_log_pattern(
                process,
                health_config.pattern,
                health_config.timeout_seconds,
                progress_callback,
            )
        elif health_config.type == "http":
            return await self._check_http(
                health_config.url,
                health_config.timeout_seconds,
            )
        elif health_config.type == "process":
            # Just check if process is still running
            await asyncio.sleep(2)
            return process.returncode is None
        else:
            logger.warning(f"Unknown health check type: {health_config.type}")
            return True

    async def _check_log_pattern(
        self,
        process: asyncio.subprocess.Process,
        pattern: Optional[str],
        timeout_seconds: int,
        progress_callback: Optional[Callable],
    ) -> bool:
        """Monitor process output for a success pattern"""
        if not pattern:
            return True

        start_time = asyncio.get_event_loop().time()
        compiled_pattern = re.compile(pattern)

        try:
            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                # Check if process has exited
                if process.returncode is not None:
                    logger.error("Process exited before health check passed")
                    return False

                # Read output with timeout
                try:
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=1.0,
                    )
                    if line:
                        line_str = line.decode("utf-8", errors="replace").strip()
                        logger.debug(f"Process output: {line_str}")

                        # Update progress with log output
                        if progress_callback:
                            elapsed = asyncio.get_event_loop().time() - start_time
                            progress = min(int((elapsed / timeout_seconds) * 100), 99)
                            await self._report_progress(
                                progress_callback,
                                "health_check",
                                progress,
                                line_str[:100],
                            )

                        # Check for pattern match
                        if compiled_pattern.search(line_str):
                            return True

                except asyncio.TimeoutError:
                    continue

            logger.error(f"Health check timed out waiting for pattern: {pattern}")
            return False

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def _check_http(self, url: Optional[str], timeout_seconds: int) -> bool:
        """Check HTTP endpoint for health"""
        if not url:
            return True

        import httpx

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=5)
                    if response.status_code < 500:
                        return True
            except Exception:
                pass

            await asyncio.sleep(2)

        return False
