"""
Kiosk mode configuration service

Handles enabling/disabling Kiosk mode for deployed applications.
Kiosk mode auto-starts the application in fullscreen on device boot.

NOTE: Kiosk mode is currently only supported on Linux systems with X11/Wayland.
Windows and macOS are not supported.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from ..models.kiosk import KioskStatus, KioskConfigResponse
from ..config import settings
from .deployment_history import deployment_history

logger = logging.getLogger(__name__)


class KioskManager:
    """Manages Kiosk mode configuration for deployments"""

    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = settings.cache_dir / "kiosk_status.json"
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensure storage file exists"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("{}")

    def _load_status(self) -> Dict[str, Any]:
        """Load all Kiosk status from storage"""
        try:
            content = self.storage_path.read_text()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to load Kiosk status: {e}")
            return {}

    def _save_status(self, statuses: Dict[str, Any]):
        """Save Kiosk status to storage"""
        try:
            content = json.dumps(statuses, indent=2, default=str)
            self.storage_path.write_text(content)
        except Exception as e:
            logger.error(f"Failed to save Kiosk status: {e}")

    async def get_status(self, deployment_id: str) -> Optional[KioskStatus]:
        """Get Kiosk status for a deployment"""
        statuses = self._load_status()
        data = statuses.get(deployment_id)

        if data:
            return KioskStatus(
                deployment_id=deployment_id,
                enabled=data.get("enabled", False),
                kiosk_user=data.get("kiosk_user"),
                app_url=data.get("app_url"),
                configured_at=datetime.fromisoformat(data["configured_at"]) if data.get("configured_at") else None,
            )

        return None

    async def configure(
        self,
        deployment_id: str,
        kiosk_user: str,
        app_url: Optional[str] = None,
        password: Optional[str] = None,
    ) -> KioskConfigResponse:
        """
        Configure Kiosk mode for a deployment

        Args:
            deployment_id: The deployment to configure
            kiosk_user: System user account to run Kiosk mode
            app_url: Application URL (defaults to deployment URL)
            password: SSH password for remote deployments

        Note:
            Kiosk mode is only supported on Linux systems. Windows and macOS
            do not have equivalent desktop autostart functionality.
        """
        try:
            # Platform check - Kiosk mode only works on Linux
            if sys.platform == "win32":
                return KioskConfigResponse(
                    success=False,
                    message="Kiosk mode is not supported on Windows. "
                            "This feature requires Linux with X11/Wayland desktop environment.",
                )
            elif sys.platform == "darwin":
                return KioskConfigResponse(
                    success=False,
                    message="Kiosk mode is not supported on macOS. "
                            "This feature requires Linux with X11/Wayland desktop environment.",
                )

            # Get deployment info
            history = await deployment_history.get_history(limit=100)
            record = next((r for r in history if r.deployment_id == deployment_id), None)

            if not record:
                return KioskConfigResponse(
                    success=False,
                    message="Deployment not found",
                )

            # Determine app URL
            if not app_url:
                metadata = record.metadata or {}
                host = metadata.get("host")
                port = metadata.get("port", 8280)

                if host:
                    app_url = f"http://{host}:{port}"
                else:
                    app_url = f"http://localhost:{port}"

            # Execute Kiosk configuration
            device_type = record.device_type
            metadata = record.metadata or {}

            if device_type == "docker_remote":
                # Remote device - execute via SSH
                success = await self._configure_remote_kiosk(
                    host=metadata.get("host"),
                    username=metadata.get("username", "recomputer"),
                    password=password,
                    kiosk_user=kiosk_user,
                    app_url=app_url,
                    solution_id=record.solution_id,
                )
            else:
                # Local device - execute directly
                success = await self._configure_local_kiosk(
                    kiosk_user=kiosk_user,
                    app_url=app_url,
                )

            if success:
                # Save status
                statuses = self._load_status()
                statuses[deployment_id] = {
                    "enabled": True,
                    "kiosk_user": kiosk_user,
                    "app_url": app_url,
                    "configured_at": datetime.utcnow().isoformat(),
                }
                self._save_status(statuses)

                status = KioskStatus(
                    deployment_id=deployment_id,
                    enabled=True,
                    kiosk_user=kiosk_user,
                    app_url=app_url,
                    configured_at=datetime.utcnow(),
                )

                return KioskConfigResponse(
                    success=True,
                    message="Kiosk mode configured successfully. Reboot to apply.",
                    status=status,
                )
            else:
                return KioskConfigResponse(
                    success=False,
                    message="Failed to configure Kiosk mode",
                )

        except Exception as e:
            logger.error(f"Failed to configure Kiosk: {e}")
            return KioskConfigResponse(
                success=False,
                message=f"Error: {str(e)}",
            )

    async def unconfigure(
        self,
        deployment_id: str,
        kiosk_user: str,
        password: Optional[str] = None,
    ) -> KioskConfigResponse:
        """
        Remove Kiosk mode configuration

        Args:
            deployment_id: The deployment to unconfigure
            kiosk_user: System user account to remove Kiosk mode from
            password: SSH password for remote deployments
        """
        try:
            # Get deployment info
            history = await deployment_history.get_history(limit=100)
            record = next((r for r in history if r.deployment_id == deployment_id), None)

            if not record:
                return KioskConfigResponse(
                    success=False,
                    message="Deployment not found",
                )

            # Execute Kiosk unconfiguration
            device_type = record.device_type
            metadata = record.metadata or {}

            if device_type == "docker_remote":
                # Remote device - execute via SSH
                success = await self._unconfigure_remote_kiosk(
                    host=metadata.get("host"),
                    username=metadata.get("username", "recomputer"),
                    password=password,
                    kiosk_user=kiosk_user,
                )
            else:
                # Local device - execute directly
                success = await self._unconfigure_local_kiosk(
                    kiosk_user=kiosk_user,
                )

            if success:
                # Update status
                statuses = self._load_status()
                if deployment_id in statuses:
                    statuses[deployment_id]["enabled"] = False
                    statuses[deployment_id]["configured_at"] = datetime.utcnow().isoformat()
                    self._save_status(statuses)

                return KioskConfigResponse(
                    success=True,
                    message="Kiosk mode disabled successfully. Reboot to apply.",
                    status=KioskStatus(
                        deployment_id=deployment_id,
                        enabled=False,
                        kiosk_user=kiosk_user,
                    ),
                )
            else:
                return KioskConfigResponse(
                    success=False,
                    message="Failed to disable Kiosk mode",
                )

        except Exception as e:
            logger.error(f"Failed to unconfigure Kiosk: {e}")
            return KioskConfigResponse(
                success=False,
                message=f"Error: {str(e)}",
            )

    async def _configure_local_kiosk(
        self,
        kiosk_user: str,
        app_url: str,
    ) -> bool:
        """Configure Kiosk mode on local machine"""
        try:
            # Find the configure script
            script_path = self._find_kiosk_script("configure_kiosk.sh")

            if script_path:
                proc = await asyncio.create_subprocess_exec(
                    "bash", script_path, kiosk_user, app_url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode == 0:
                    logger.info(f"Kiosk configured for {kiosk_user}")
                    return True
                else:
                    logger.error(f"Kiosk config failed: {stderr.decode()}")
                    return False
            else:
                # Manual configuration fallback
                logger.warning("Kiosk script not found, using fallback")
                return await self._configure_kiosk_manually(kiosk_user, app_url)

        except Exception as e:
            logger.error(f"Local Kiosk configuration failed: {e}")
            return False

    async def _unconfigure_local_kiosk(
        self,
        kiosk_user: str,
    ) -> bool:
        """Remove Kiosk mode from local machine"""
        try:
            script_path = self._find_kiosk_script("unconfigure_kiosk.sh")

            if script_path:
                proc = await asyncio.create_subprocess_exec(
                    "bash", script_path, kiosk_user,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()

                if proc.returncode == 0:
                    logger.info(f"Kiosk unconfigured for {kiosk_user}")
                    return True
                else:
                    logger.error(f"Kiosk unconfig failed: {stderr.decode()}")
                    return False
            else:
                # Manual unconfiguration fallback
                return await self._unconfigure_kiosk_manually(kiosk_user)

        except Exception as e:
            logger.error(f"Local Kiosk unconfiguration failed: {e}")
            return False

    async def _get_remote_home_dir(self, client, kiosk_user: str) -> Optional[str]:
        """Get the home directory of a user on remote system"""
        try:
            # Use getent to get user's home directory (works on Linux/OpenWrt)
            stdin, stdout, stderr = await asyncio.to_thread(
                client.exec_command,
                f"getent passwd {kiosk_user} | cut -d: -f6",
                timeout=10
            )
            exit_code = stdout.channel.recv_exit_status()
            if exit_code == 0:
                home_dir = stdout.read().decode().strip()
                if home_dir:
                    return home_dir

            # Fallback: use eval echo ~user
            stdin, stdout, stderr = await asyncio.to_thread(
                client.exec_command,
                f"eval echo ~{kiosk_user}",
                timeout=10
            )
            exit_code = stdout.channel.recv_exit_status()
            if exit_code == 0:
                home_dir = stdout.read().decode().strip()
                if home_dir and not home_dir.startswith("~"):
                    return home_dir

            # Last resort: assume /home/{user}
            return f"/home/{kiosk_user}"
        except Exception as e:
            logger.warning(f"Failed to get remote home dir, using default: {e}")
            return f"/home/{kiosk_user}"

    async def _configure_remote_kiosk(
        self,
        host: str,
        username: str,
        password: Optional[str],
        kiosk_user: str,
        app_url: str,
        solution_id: str,
    ) -> bool:
        """Configure Kiosk mode on remote device via SSH"""
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Connect
            await asyncio.to_thread(
                client.connect,
                hostname=host,
                port=22,
                username=username,
                password=password,
                timeout=30,
            )

            try:
                # Get the actual home directory for kiosk_user
                home_dir = await self._get_remote_home_dir(client, kiosk_user)
                logger.info(f"Remote home directory for {kiosk_user}: {home_dir}")

                # Create kiosk script content (with dynamic home path)
                kiosk_script = self._generate_kiosk_script(app_url)
                autostart_content = self._generate_autostart_desktop_with_home(kiosk_user, home_dir)

                # Execute configuration commands
                commands = [
                    f"mkdir -p {home_dir}/.local/bin",
                    f"mkdir -p {home_dir}/.config/autostart",
                    f"cat > {home_dir}/.local/bin/kiosk.sh << 'KIOSK_EOF'\n{kiosk_script}\nKIOSK_EOF",
                    f"chmod +x {home_dir}/.local/bin/kiosk.sh",
                    f"cat > {home_dir}/.config/autostart/kiosk.desktop << 'DESKTOP_EOF'\n{autostart_content}\nDESKTOP_EOF",
                    f"chown -R {kiosk_user}:{kiosk_user} {home_dir}/.local/bin/kiosk.sh",
                    f"chown -R {kiosk_user}:{kiosk_user} {home_dir}/.config/autostart/kiosk.desktop",
                ]

                for cmd in commands:
                    stdin, stdout, stderr = await asyncio.to_thread(
                        client.exec_command, cmd, timeout=30
                    )
                    exit_code = stdout.channel.recv_exit_status()

                    if exit_code != 0:
                        error = stderr.read().decode()
                        logger.error(f"Remote Kiosk config failed: {error}")
                        return False

                logger.info(f"Remote Kiosk configured for {kiosk_user} on {host}")
                return True

            finally:
                client.close()

        except ImportError:
            logger.error("paramiko not installed")
            return False
        except Exception as e:
            logger.error(f"Remote Kiosk configuration failed: {e}")
            return False

    async def _unconfigure_remote_kiosk(
        self,
        host: str,
        username: str,
        password: Optional[str],
        kiosk_user: str,
    ) -> bool:
        """Remove Kiosk mode from remote device via SSH"""
        try:
            import paramiko

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            await asyncio.to_thread(
                client.connect,
                hostname=host,
                port=22,
                username=username,
                password=password,
                timeout=30,
            )

            try:
                # Get the actual home directory for kiosk_user
                home_dir = await self._get_remote_home_dir(client, kiosk_user)

                commands = [
                    f"rm -f {home_dir}/.config/autostart/kiosk.desktop",
                    f"rm -f {home_dir}/.local/bin/kiosk.sh",
                ]

                for cmd in commands:
                    stdin, stdout, stderr = await asyncio.to_thread(
                        client.exec_command, cmd, timeout=30
                    )
                    stdout.channel.recv_exit_status()

                logger.info(f"Remote Kiosk unconfigured for {kiosk_user} on {host}")
                return True

            finally:
                client.close()

        except ImportError:
            logger.error("paramiko not installed")
            return False
        except Exception as e:
            logger.error(f"Remote Kiosk unconfiguration failed: {e}")
            return False

    def _find_kiosk_script(self, script_name: str) -> Optional[str]:
        """Find Kiosk script in solution assets"""
        # Look in common locations
        search_paths = [
            settings.solutions_dir,
            Path(__file__).parent.parent / "solutions",
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            for script_path in base_path.rglob(f"**/scripts/{script_name}"):
                if script_path.is_file():
                    return str(script_path)

        return None

    def _generate_kiosk_script(self, app_url: str) -> str:
        """Generate Kiosk launch script content"""
        return f'''#!/bin/bash
# HVAC Kiosk Launcher

# Wait for network and services to be ready
sleep 15

# Disable screen saver and power management
xset s off
xset -dpms
xset s noblank

# Start fullscreen browser
if command -v chromium-browser &> /dev/null; then
    chromium-browser --kiosk --noerrdialogs --disable-infobars \\
        --disable-session-crashed-bubble --disable-restore-session-state \\
        --check-for-update-interval=31536000 \\
        "{app_url}"
elif command -v chromium &> /dev/null; then
    chromium --kiosk --noerrdialogs --disable-infobars \\
        --disable-session-crashed-bubble --disable-restore-session-state \\
        --check-for-update-interval=31536000 \\
        "{app_url}"
elif command -v firefox &> /dev/null; then
    firefox --kiosk "{app_url}"
else
    echo "No supported browser found"
    exit 1
fi
'''

    def _generate_autostart_desktop(self, kiosk_user: str) -> str:
        """Generate autostart desktop entry content (for local use)"""
        import os
        home_dir = os.path.expanduser(f"~{kiosk_user}")
        return self._generate_autostart_desktop_with_home(kiosk_user, home_dir)

    def _generate_autostart_desktop_with_home(self, kiosk_user: str, home_dir: str) -> str:
        """Generate autostart desktop entry content with explicit home directory"""
        return f'''[Desktop Entry]
Type=Application
Name=HVAC Kiosk
Comment=HVAC Automation Control System Kiosk Mode
Exec={home_dir}/.local/bin/kiosk.sh
X-GNOME-Autostart-enabled=true
Hidden=false
NoDisplay=false
'''

    def _get_local_home_dir(self, kiosk_user: str) -> Path:
        """Get the home directory of a local user"""
        import os
        # Try to expand ~user
        home_dir = os.path.expanduser(f"~{kiosk_user}")
        if home_dir.startswith("~"):
            # Expansion failed, fall back to /home/{user}
            return Path(f"/home/{kiosk_user}")
        return Path(home_dir)

    async def _configure_kiosk_manually(self, kiosk_user: str, app_url: str) -> bool:
        """Fallback manual Kiosk configuration"""
        try:
            home_dir = self._get_local_home_dir(kiosk_user)
            script_content = self._generate_kiosk_script(app_url)
            autostart_content = self._generate_autostart_desktop_with_home(kiosk_user, str(home_dir))

            script_dir = home_dir / ".local" / "bin"
            autostart_dir = home_dir / ".config" / "autostart"

            script_dir.mkdir(parents=True, exist_ok=True)
            autostart_dir.mkdir(parents=True, exist_ok=True)

            (script_dir / "kiosk.sh").write_text(script_content)
            (script_dir / "kiosk.sh").chmod(0o755)

            (autostart_dir / "kiosk.desktop").write_text(autostart_content)

            return True

        except Exception as e:
            logger.error(f"Manual Kiosk configuration failed: {e}")
            return False

    async def _unconfigure_kiosk_manually(self, kiosk_user: str) -> bool:
        """Fallback manual Kiosk unconfiguration"""
        try:
            home_dir = self._get_local_home_dir(kiosk_user)
            script_path = home_dir / ".local" / "bin" / "kiosk.sh"
            autostart_path = home_dir / ".config" / "autostart" / "kiosk.desktop"

            if script_path.exists():
                script_path.unlink()
            if autostart_path.exists():
                autostart_path.unlink()

            return True

        except Exception as e:
            logger.error(f"Manual Kiosk unconfiguration failed: {e}")
            return False


# Global instance
kiosk_manager = KioskManager()
