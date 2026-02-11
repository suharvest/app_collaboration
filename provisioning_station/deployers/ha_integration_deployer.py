"""
Home Assistant integration deployer

Deploys reCamera custom component to an existing Home Assistant instance.
Supports both HA OS (auto-installs SSH addon) and Docker Core (uses direct SSH).

Flow:
1. Authenticate to HA via login flow API
2. Detect HA type (HAOS vs Docker Core) via Supervisor API
3. Ensure SSH access:
   - HAOS: check/install/configure/start SSH addon
   - Docker: use provided SSH credentials
4. Copy custom_components files via tar+base64 over SSH
5. Restart HA via REST API
6. Wait for HA to come back, re-authenticate
7. Add reCamera integration via config flow API
"""

import asyncio
import base64
import io
import json
import logging
import tarfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from ..models.device import DeviceConfig
from .base import BaseDeployer

logger = logging.getLogger(__name__)

# SSH addon slugs in order of preference (for install fallback)
HAOS_SSH_INSTALL_SLUG = "core_ssh"

# Known SSH addon slugs and their username patterns
# Note: Community addon slugs vary by repository (a0d7b954, fb59d657, etc.)
# so we scan by name instead of hardcoding all slugs.
CORE_SSH_USERNAME = "root"


class HAIntegrationDeployer(BaseDeployer):
    """Deploys reCamera custom component to an existing Home Assistant instance."""

    async def deploy(
        self,
        config: DeviceConfig,
        connection: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        ha_host = connection["host"]
        ha_port = int(connection.get("ha_port", 8123))
        ha_username = connection["username"]
        ha_password = connection["password"]
        recamera_ip = connection.get("recamera_ip", "192.168.42.1")
        recamera_port = int(connection.get("recamera_port", 1880))

        # Optional: SSH credentials for Docker-on-Linux
        ssh_username = connection.get("ssh_username")
        ssh_password = connection.get("ssh_password")
        config_dir = connection.get("config_dir", "/config")

        ha_url = f"http://{ha_host}:{ha_port}"

        # Resolve custom_components source path
        components_dir = self._get_components_path(config)
        if not components_dir:
            raise RuntimeError(
                "Cannot find custom_components directory in solution assets"
            )

        # --- Step 1: Authenticate to HA ---
        await self._report_progress(
            progress_callback, "auth", 0, "Authenticating to Home Assistant..."
        )
        token = await self._ha_login(ha_url, ha_username, ha_password)
        await self._report_progress(
            progress_callback, "auth", 100, "Authenticated successfully"
        )

        # --- Step 2: Detect HA type ---
        await self._report_progress(
            progress_callback, "detect", 0, "Detecting Home Assistant type..."
        )
        is_haos = await self._detect_haos(ha_url, token)
        ha_type = "HA OS" if is_haos else "Docker Core"
        await self._report_progress(
            progress_callback, "detect", 100, f"Detected: {ha_type}"
        )

        # --- Step 3: Ensure SSH access ---
        if is_haos:
            await self._report_progress(
                progress_callback, "ssh", 0, "Checking SSH addon..."
            )
            ssh_info = await self._ensure_haos_ssh(ha_url, token, progress_callback)
            ssh_conn = {
                "host": ha_host,
                "port": ssh_info["port"],
                "username": ssh_info["username"],
                "password": ssh_info["password"],
            }
            use_sudo = True
        else:
            if not ssh_username or not ssh_password:
                raise RuntimeError(
                    "SSH credentials required for Docker HA. "
                    "Please provide ssh_username and ssh_password."
                )
            ssh_conn = {
                "host": connection.get("ssh_host", ha_host),
                "port": int(connection.get("ssh_port", 22)),
                "username": ssh_username,
                "password": ssh_password,
            }
            use_sudo = False
            await self._report_progress(
                progress_callback, "ssh", 100, "Using provided SSH credentials"
            )

        # --- Step 4: Copy custom_components via SSH ---
        await self._report_progress(
            progress_callback, "copy", 0, "Copying reCamera integration files..."
        )
        if is_haos:
            await self._copy_components_ssh(
                ssh_conn, config_dir, components_dir, use_sudo=True
            )
        else:
            await self._copy_via_docker(ssh_conn, components_dir)
        await self._report_progress(
            progress_callback, "copy", 100, "Integration files copied"
        )

        # --- Step 5: Restart HA ---
        await self._report_progress(
            progress_callback, "restart", 0, "Restarting Home Assistant..."
        )
        await self._restart_ha(ha_url, token)

        # --- Step 6: Wait for HA to come back ---
        await self._report_progress(
            progress_callback, "restart", 30, "Waiting for Home Assistant to restart..."
        )
        await self._wait_for_ha(ha_url, timeout=120)
        await self._report_progress(
            progress_callback, "restart", 70, "Home Assistant is back online"
        )

        # Re-authenticate (old token invalid after restart)
        token = await self._ha_login(ha_url, ha_username, ha_password)
        await self._report_progress(
            progress_callback, "restart", 100, "Re-authenticated after restart"
        )

        # --- Step 7: Add reCamera integration ---
        await self._report_progress(
            progress_callback, "integrate", 0, "Adding reCamera integration..."
        )
        await self._add_recamera_integration(ha_url, token, recamera_ip, recamera_port)
        await self._report_progress(
            progress_callback,
            "integrate",
            100,
            "reCamera integration added successfully!",
        )

        return True

    # -------------------------------------------------------------------------
    # HA Authentication
    # -------------------------------------------------------------------------

    async def _ha_login(self, ha_url: str, username: str, password: str) -> str:
        """Authenticate to HA via login flow and return access token."""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1: Start login flow
            resp = await client.post(
                f"{ha_url}/auth/login_flow",
                json={
                    "client_id": f"{ha_url}/",
                    "handler": ["homeassistant", None],
                    "redirect_uri": f"{ha_url}/",
                },
            )
            resp.raise_for_status()
            flow_id = resp.json()["flow_id"]

            # Step 2: Submit credentials
            resp = await client.post(
                f"{ha_url}/auth/login_flow/{flow_id}",
                json={
                    "client_id": f"{ha_url}/",
                    "username": username,
                    "password": password,
                },
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("type") == "create_entry":
                auth_code = result["result"]
            else:
                errors = result.get("errors", {})
                raise RuntimeError(
                    f"HA login failed: {errors.get('base', 'unknown error')}"
                )

            # Step 3: Exchange auth code for token
            resp = await client.post(
                f"{ha_url}/auth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "client_id": f"{ha_url}/",
                },
            )
            resp.raise_for_status()
            return resp.json()["access_token"]

    # -------------------------------------------------------------------------
    # HA Type Detection
    # -------------------------------------------------------------------------

    async def _detect_haos(self, ha_url: str, token: str) -> bool:
        """Detect if HA is running on HA OS (has Supervisor) or Docker Core."""
        try:
            result = await self._supervisor_api(ha_url, token, "/info", "get")
            return result is not None
        except Exception:
            return False

    async def _supervisor_api(
        self,
        ha_url: str,
        token: str,
        endpoint: str,
        method: str,
        data: Optional[dict] = None,
        timeout: float = 30,
    ) -> Optional[dict]:
        """Call HA Supervisor API via WebSocket."""
        import websockets

        ws_url = ha_url.replace("http://", "ws://") + "/api/websocket"

        async with websockets.connect(ws_url, close_timeout=5) as ws:
            # Authenticate
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            if msg.get("type") != "auth_required":
                raise RuntimeError(f"Unexpected WS message: {msg}")

            await ws.send(json.dumps({"type": "auth", "access_token": token}))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
            if msg.get("type") != "auth_ok":
                raise RuntimeError(f"WS auth failed: {msg}")

            # Send Supervisor API request
            request = {
                "id": 1,
                "type": "supervisor/api",
                "endpoint": endpoint,
                "method": method,
            }
            if data is not None:
                request["data"] = data

            await ws.send(json.dumps(request))
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))

            if msg.get("success"):
                return msg.get("result")
            else:
                error = msg.get("error", {})
                raise RuntimeError(
                    f"Supervisor API error: {error.get('message', 'unknown')}"
                )

    # -------------------------------------------------------------------------
    # HAOS SSH Addon Management
    # -------------------------------------------------------------------------

    async def _ensure_haos_ssh(
        self, ha_url: str, token: str, progress_callback: Optional[Callable]
    ) -> Dict[str, Any]:
        """Ensure SSH addon is installed, configured, and running on HAOS.

        Returns dict with host, port, username, password for SSH connection.
        """
        # Check installed addons — scan by name, not hardcoded slugs
        result = await self._supervisor_api(ha_url, token, "/addons", "get")
        addons = result.get("addons", [])

        # Find any installed SSH addon (core_ssh, or community variants like
        # a0d7b954_ssh, fb59d657_ssh — slugs vary by repo)
        ssh_addon = None
        for addon in addons:
            slug = addon.get("slug", "")
            name = addon.get("name", "").lower()
            if slug == "core_ssh" or (
                slug.endswith("_ssh") and ("terminal" in name or "ssh" in name)
            ):
                ssh_addon = addon
                logger.info(f"Found SSH addon: {slug} ({addon.get('name')})")
                break

        if ssh_addon is None:
            # Install SSH addon
            await self._report_progress(
                progress_callback,
                "ssh",
                20,
                "Installing SSH addon (this may take a minute)...",
            )
            slug = HAOS_SSH_INSTALL_SLUG
            await self._supervisor_api(
                ha_url,
                token,
                f"/addons/{slug}/install",
                "post",
                timeout=120,
            )
            logger.info(f"Installed SSH addon: {slug}")

            # Configure with temporary password
            temp_password = f"recamera-{uuid4().hex[:8]}"
            await self._supervisor_api(
                ha_url,
                token,
                f"/addons/{slug}/options",
                "post",
                data={
                    "options": {
                        "password": temp_password,
                        "authorized_keys": [],
                        "sftp": False,
                    }
                },
            )

            # Start addon
            await self._report_progress(
                progress_callback, "ssh", 60, "Starting SSH addon..."
            )
            await self._supervisor_api(
                ha_url, token, f"/addons/{slug}/start", "post", timeout=60
            )

            # Wait for SSH to be ready
            await asyncio.sleep(3)

            await self._report_progress(
                progress_callback, "ssh", 100, "SSH addon installed and started"
            )

            return {
                "username": CORE_SSH_USERNAME,
                "password": temp_password,
                "port": 22,
            }

        # SSH addon already installed
        slug = ssh_addon["slug"]
        logger.info(f"Found existing SSH addon: {slug} (state: {ssh_addon['state']})")

        # Start if not running
        if ssh_addon["state"] != "started":
            await self._report_progress(
                progress_callback, "ssh", 40, f"Starting SSH addon ({slug})..."
            )
            await self._supervisor_api(
                ha_url, token, f"/addons/{slug}/start", "post", timeout=60
            )
            await asyncio.sleep(3)

        # Get addon options to extract SSH credentials
        info = await self._supervisor_api(ha_url, token, f"/addons/{slug}/info", "get")
        options = info.get("options", {})

        if slug == "core_ssh":
            username = CORE_SSH_USERNAME
            password = options.get("password", "")
        else:
            # Advanced SSH addon has nested ssh config
            ssh_opts = options.get("ssh", options)
            username = ssh_opts.get("username", "root")
            password = ssh_opts.get("password", "")

        if not password:
            # No password set — configure a temporary one
            logger.info(f"SSH addon {slug} has no password, setting temporary password")
            temp_password = f"recamera-{uuid4().hex[:8]}"

            if slug == "core_ssh":
                new_options = {**options, "password": temp_password}
            else:
                ssh_opts = options.get("ssh", {})
                ssh_opts["password"] = temp_password
                new_options = {**options, "ssh": ssh_opts}

            await self._supervisor_api(
                ha_url,
                token,
                f"/addons/{slug}/options",
                "post",
                data={"options": new_options},
            )
            # Restart addon to pick up new password
            await self._supervisor_api(
                ha_url, token, f"/addons/{slug}/restart", "post", timeout=60
            )
            await asyncio.sleep(3)
            password = temp_password

        await self._report_progress(
            progress_callback, "ssh", 100, f"SSH addon ready ({slug})"
        )

        return {"username": username, "password": password, "port": 22}

    # -------------------------------------------------------------------------
    # File Copy via SSH
    # -------------------------------------------------------------------------

    async def _copy_components_ssh(
        self,
        ssh_conn: Dict[str, Any],
        config_dir: str,
        components_dir: str,
        use_sudo: bool,
    ):
        """Copy custom_components/recamera/ files to HA via SSH using tar+base64."""
        import paramiko

        # Build tar archive in memory
        tar_buffer = io.BytesIO()
        src_path = Path(components_dir)
        files_added = []
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            for f in sorted(src_path.iterdir()):
                if f.is_file() and (
                    f.suffix == ".py"
                    or f.name == "manifest.json"
                    or f.name == "strings.json"
                ):
                    tar.add(str(f), arcname=f.name)
                    files_added.append(f.name)

        if not files_added:
            raise RuntimeError(f"No component files found in {components_dir}")

        logger.info(f"Packed {len(files_added)} files: {files_added}")
        tar_data = tar_buffer.getvalue()
        b64_data = base64.b64encode(tar_data)

        # SSH connect and copy
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            await asyncio.to_thread(
                client.connect,
                hostname=ssh_conn["host"],
                port=ssh_conn["port"],
                username=ssh_conn["username"],
                password=ssh_conn["password"],
                timeout=15,
            )

            dest = f"{config_dir}/custom_components/recamera"
            sudo = "sudo " if use_sudo else ""

            # Create directory
            await self._ssh_exec(client, f"{sudo}mkdir -p {dest}")

            # Transfer files via base64 pipe
            cmd = f"{sudo}sh -c 'base64 -d | tar xf - -C {dest}'"
            stdin, stdout, stderr = await asyncio.to_thread(client.exec_command, cmd)
            await asyncio.to_thread(stdin.write, b64_data)
            await asyncio.to_thread(stdin.channel.shutdown_write)
            exit_status = await asyncio.to_thread(stdout.channel.recv_exit_status)
            if exit_status != 0:
                err = (await asyncio.to_thread(stderr.read)).decode()
                raise RuntimeError(f"File transfer failed (exit {exit_status}): {err}")

            # Clean up macOS ._ metadata files
            await self._ssh_exec(
                client, f"{sudo}rm -f {dest}/._* 2>/dev/null", ignore_error=True
            )

            # Verify files
            result = await self._ssh_exec(client, f"ls {dest}/")
            logger.info(f"Files on HA: {result.strip()}")

        finally:
            client.close()

    async def _ssh_exec(
        self,
        client,
        cmd: str,
        ignore_error: bool = False,
    ) -> str:
        """Execute SSH command and return stdout."""
        stdin, stdout, stderr = await asyncio.to_thread(client.exec_command, cmd)
        exit_status = await asyncio.to_thread(stdout.channel.recv_exit_status)
        out = (await asyncio.to_thread(stdout.read)).decode()
        if exit_status != 0 and not ignore_error:
            err = (await asyncio.to_thread(stderr.read)).decode()
            raise RuntimeError(f"SSH command failed: {cmd}\n{err}")
        return out

    # -------------------------------------------------------------------------
    # HA Restart & Wait
    # -------------------------------------------------------------------------

    async def _restart_ha(self, ha_url: str, token: str):
        """Restart Home Assistant via REST API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{ha_url}/api/services/homeassistant/restart",
                    headers={"Authorization": f"Bearer {token}"},
                )
                # 200 = success; 502/503/504 = HA already shutting down (expected)
                if resp.status_code not in (200, 502, 503, 504):
                    resp.raise_for_status()
        except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError):
            # Connection reset during restart is expected
            logger.info("HA connection closed during restart (expected)")

    async def _wait_for_ha(self, ha_url: str, timeout: int = 180):
        """Wait for HA to come back online after restart.

        On HA OS, the entire Supervisor stack restarts, not just HA Core,
        so this can take 30-90 seconds. We poll the root URL which returns
        200 when ready, or 302 for onboarding.
        """
        import httpx

        start = asyncio.get_event_loop().time()
        # HA needs a few seconds to actually start shutting down
        await asyncio.sleep(10)

        while (asyncio.get_event_loop().time() - start) < timeout:
            try:
                async with httpx.AsyncClient(
                    timeout=5, follow_redirects=False
                ) as client:
                    resp = await client.get(ha_url)
                    # 200 = HA ready, 302 = redirect to onboarding/login, 401 = API auth
                    if resp.status_code in (200, 302, 401):
                        logger.info(f"HA is back online (HTTP {resp.status_code})")
                        # Give HA a few more seconds to finish loading integrations
                        await asyncio.sleep(5)
                        return
            except Exception:
                pass
            await asyncio.sleep(5)

        raise RuntimeError(
            f"Home Assistant did not come back within {timeout}s after restart"
        )

    # -------------------------------------------------------------------------
    # Add reCamera Integration
    # -------------------------------------------------------------------------

    async def _add_recamera_integration(
        self, ha_url: str, token: str, recamera_ip: str, recamera_port: int = 1880
    ):
        """Add reCamera integration via HA config flow API."""
        import httpx

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            # Check if integration already exists
            resp = await client.get(
                f"{ha_url}/api/config/config_entries/entry",
                headers=headers,
            )
            if resp.status_code == 200:
                entries = resp.json()
                for entry in entries:
                    if entry.get("domain") == "recamera":
                        logger.info("reCamera integration already configured, skipping")
                        return

            # Start config flow
            resp = await client.post(
                f"{ha_url}/api/config/config_entries/flow",
                headers=headers,
                json={"handler": "recamera", "show_advanced_options": False},
            )
            resp.raise_for_status()
            flow = resp.json()
            flow_id = flow["flow_id"]

            # Submit form with reCamera IP
            resp = await client.post(
                f"{ha_url}/api/config/config_entries/flow/{flow_id}",
                headers=headers,
                json={"host": recamera_ip, "port": recamera_port},
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("type") == "create_entry":
                logger.info(f"reCamera integration created: {result.get('title', '')}")
            else:
                errors = result.get("errors", {})
                if errors:
                    raise RuntimeError(f"Failed to add reCamera integration: {errors}")
                logger.warning(f"Unexpected config flow result: {result}")

    # -------------------------------------------------------------------------
    # Docker Copy (for Docker Core HA)
    # -------------------------------------------------------------------------

    async def _find_ha_container(self, client) -> str:
        """Find the Home Assistant container name on the Docker host."""
        # Try our known container name first
        for search in [
            "docker ps --format '{{.Names}}' --filter name=recamera-homeassistant",
            "docker ps --format '{{.Names}}' --filter name=homeassistant",
        ]:
            result = await self._ssh_exec(client, search, ignore_error=True)
            name = result.strip().split("\n")[0].strip()
            if name:
                return name

        # Search by image
        result = await self._ssh_exec(
            client,
            "docker ps --format '{{.Names}}' | grep -i homeassistant | head -1",
            ignore_error=True,
        )
        name = result.strip()
        if name:
            return name

        raise RuntimeError(
            "Cannot find Home Assistant Docker container. Is it running?"
        )

    async def _copy_via_docker(self, ssh_conn: Dict[str, Any], components_dir: str):
        """Copy custom_components into HA Docker container via docker exec."""
        import paramiko

        # Build tar archive in memory
        tar_buffer = io.BytesIO()
        src_path = Path(components_dir)
        files_added = []
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            for f in sorted(src_path.iterdir()):
                if f.is_file() and (
                    f.suffix == ".py"
                    or f.name == "manifest.json"
                    or f.name == "strings.json"
                ):
                    tar.add(str(f), arcname=f.name)
                    files_added.append(f.name)

        if not files_added:
            raise RuntimeError(f"No component files found in {components_dir}")

        logger.info(f"Packed {len(files_added)} files: {files_added}")
        tar_data = tar_buffer.getvalue()
        b64_data = base64.b64encode(tar_data)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            await asyncio.to_thread(
                client.connect,
                hostname=ssh_conn["host"],
                port=ssh_conn["port"],
                username=ssh_conn["username"],
                password=ssh_conn["password"],
                timeout=15,
            )

            # Find the HA container
            container = await self._find_ha_container(client)
            logger.info(f"Found HA container: {container}")

            dest = "/config/custom_components/recamera"

            # Create directory and extract files inside the container
            await self._ssh_exec(
                client,
                f"docker exec {container} mkdir -p {dest}",
            )

            cmd = (
                f"docker exec -i {container} " f"sh -c 'base64 -d | tar xf - -C {dest}'"
            )
            stdin, stdout, stderr = await asyncio.to_thread(client.exec_command, cmd)
            await asyncio.to_thread(stdin.write, b64_data)
            await asyncio.to_thread(stdin.channel.shutdown_write)
            exit_status = await asyncio.to_thread(stdout.channel.recv_exit_status)
            if exit_status != 0:
                err = (await asyncio.to_thread(stderr.read)).decode()
                raise RuntimeError(f"Docker copy failed (exit {exit_status}): {err}")

            # Verify files
            result = await self._ssh_exec(client, f"docker exec {container} ls {dest}/")
            logger.info(f"Files in container: {result.strip()}")

        finally:
            client.close()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_components_path(self, config: DeviceConfig) -> Optional[str]:
        """Get the path to custom_components/recamera/ in solution assets."""
        if not config.base_path:
            return None

        # Try the standard path (base_path points to solution root)
        components_dir = (
            Path(config.base_path)
            / "assets"
            / "docker"
            / "custom_components"
            / "recamera"
        ).resolve()

        if components_dir.is_dir():
            return str(components_dir)

        # Try relative to ha_integration config
        if hasattr(config, "ha_integration") and config.ha_integration:
            custom_path = config.get_asset_path(config.ha_integration.components_dir)
            if custom_path and Path(custom_path).is_dir():
                return custom_path

        return None
