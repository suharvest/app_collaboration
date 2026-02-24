"""
Action executor classes for the unified actions system.

Provides local (subprocess) and SSH (paramiko) execution of actions
defined in device YAML configs.
"""

import asyncio
import logging
import os
import shlex
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.device import ActionConfig, ActionCopy
from ..utils.template import build_sudo_cmd as _build_sudo_cmd
from ..utils.template import substitute as _substitute

logger = logging.getLogger(__name__)


class ActionExecutor(ABC):
    """Abstract base for action execution."""

    @abstractmethod
    async def execute_run(
        self,
        action: ActionConfig,
        context: Dict[str, Any],
        cwd: Optional[str] = None,
    ) -> bool:
        """Execute a 'run' action. Returns True on success."""
        pass

    @abstractmethod
    async def execute_copy(
        self,
        copy: ActionCopy,
        context: Dict[str, Any],
        base_path: Optional[str] = None,
    ) -> bool:
        """Execute a 'copy' action. Returns True on success."""
        pass


class LocalActionExecutor(ActionExecutor):
    """Execute actions locally via subprocess."""

    async def execute_run(
        self,
        action: ActionConfig,
        context: Dict[str, Any],
        cwd: Optional[str] = None,
    ) -> bool:
        cmd = _substitute(action.run, context)
        if not cmd:
            return True

        env = os.environ.copy()
        for k, v in action.env.items():
            env[k] = _substitute(v, context)

        try:
            if sys.platform == "win32":
                process = await asyncio.create_subprocess_exec(
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    "/bin/sh",
                    "-c",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=env,
                )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=action.timeout
            )

            if process.returncode != 0:
                logger.error(
                    f"Action '{action.name}' failed (exit {process.returncode}): "
                    f"{stderr.decode('utf-8', errors='replace')[:500]}"
                )
                return False

            return True

        except asyncio.TimeoutError:
            logger.error(f"Action '{action.name}' timed out after {action.timeout}s")
            try:
                process.kill()
            except Exception:
                pass
            return False
        except Exception as e:
            logger.error(f"Action '{action.name}' failed: {e}")
            return False

    async def execute_copy(
        self,
        copy: ActionCopy,
        context: Dict[str, Any],
        base_path: Optional[str] = None,
    ) -> bool:
        src = _substitute(copy.src, context)
        dest = _substitute(copy.dest, context)

        if base_path and not os.path.isabs(src):
            src = str(Path(base_path) / src)

        try:
            dest_path = Path(dest)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

            # Set file mode
            if copy.mode:
                os.chmod(dest, int(copy.mode, 8))

            return True
        except Exception as e:
            logger.error(f"Copy failed ({src} -> {dest}): {e}")
            return False


class SSHActionExecutor(ActionExecutor):
    """Execute actions remotely via SSH (paramiko)."""

    def __init__(self, client, password: Optional[str] = None):
        self._client = client
        self._password = password

    async def execute_run(
        self,
        action: ActionConfig,
        context: Dict[str, Any],
        cwd: Optional[str] = None,
    ) -> bool:
        cmd = _substitute(action.run, context)
        if not cmd:
            return True

        # Prepend env vars
        env_parts = []
        for k, v in action.env.items():
            val = _substitute(v, context)
            env_parts.append(f"{k}={shlex.quote(val)}")
        env_prefix = f"env {' '.join(env_parts)} " if env_parts else ""

        # Ignore cwd for SSH — it's always a local solution path that
        # doesn't exist on the remote device.  Remote action scripts
        # should use absolute paths.
        full_cmd = f"{env_prefix}{cmd}"

        # Wrap with sudo if needed
        if action.sudo and self._password:
            full_cmd = _build_sudo_cmd(self._password, f"sh -c {shlex.quote(full_cmd)}")

        try:
            exit_code, stdout, stderr = await asyncio.to_thread(
                self._exec_with_timeout, full_cmd, action.timeout
            )

            if exit_code != 0:
                logger.error(
                    f"SSH action '{action.name}' failed (exit {exit_code}): "
                    f"{stderr[:500]}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"SSH action '{action.name}' failed: {e}")
            return False

    async def execute_copy(
        self,
        copy: ActionCopy,
        context: Dict[str, Any],
        base_path: Optional[str] = None,
    ) -> bool:
        src = _substitute(copy.src, context)
        dest = _substitute(copy.dest, context)

        if base_path and not os.path.isabs(src):
            src = str(Path(base_path) / src)

        try:
            from scp import SCPClient

            # Ensure remote directory exists
            dest_dir = str(Path(dest).parent)
            mkdir_cmd = f"mkdir -p {shlex.quote(dest_dir)}"
            if self._password:
                mkdir_cmd = _build_sudo_cmd(self._password, mkdir_cmd)
            await asyncio.to_thread(self._exec_with_timeout, mkdir_cmd, 30)

            # SCP the file
            with SCPClient(self._client.get_transport()) as scp:
                await asyncio.to_thread(scp.put, src, dest)

            # Set permissions
            if copy.mode:
                chmod_cmd = f"chmod {copy.mode} {shlex.quote(dest)}"
                if self._password:
                    chmod_cmd = _build_sudo_cmd(self._password, chmod_cmd)
                await asyncio.to_thread(self._exec_with_timeout, chmod_cmd, 30)

            return True
        except Exception as e:
            logger.error(f"SSH copy failed ({src} -> {dest}): {e}")
            return False

    def _exec_with_timeout(self, cmd: str, timeout: int = 300) -> tuple:
        """Execute command with timeout (blocking, run in thread)."""
        try:
            stdin, stdout, stderr = self._client.exec_command(cmd, timeout=timeout)
            stdout.channel.settimeout(timeout)
            stderr.channel.settimeout(timeout)

            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode()
            stderr_data = stderr.read().decode()

            return exit_code, stdout_data, stderr_data
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)
