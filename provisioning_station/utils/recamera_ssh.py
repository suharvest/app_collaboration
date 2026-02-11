"""
reCamera SSH utilities

Shared SSH operations for reCamera devices, used by both:
- ReCameraNodeRedDeployer (pre-deploy cleanup)
- RestoreManager (factory restore)

Uses exclusion approach: a whitelist of known system services protects
factory init scripts. Anything NOT in the whitelist is treated as a
third-party deployed service and will be stopped/disabled/removed.
"""

import asyncio
import logging
import shlex
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

# Node-RED related services that need to be enabled
NODERED_SERVICES = [
    "node-red",
    "sscma-node",
    "sscma-supervisor",
]

# reCamera factory system init scripts.
# Matching rule: a service is whitelisted if its name (after stripping S/K + digits)
# STARTS WITH any entry in this set.
# Verified against reCamera /etc/init.d/ contents.
SYSTEM_SERVICES_WHITELIST = {
    # Node-RED ecosystem (managed separately)
    "node-red",
    "sscma-node",
    "sscma-supervisor",
    # Core system services
    "syslogd",
    "klogd",
    "sysctl",
    "network",
    "dbus",
    "avahi",
    "dnsmasq",
    "dropbear",
    "sshd",
    "ntp",
    "crond",
    "udev",
    "urandom",
    "mosquitto",
    "dhcpcd",
    "hostapd",
    "wpa_supplicant",
    "ttyd",
    "connman",
    "user",
    # Hardware / driver services
    "hardware",
    "bt-init",
    "bt_init",
    "bluetooth",
    "modules",
    "loadmodules",
    "gpio",
    "i2c",
    "spi",
    "usb",
    "alsa",
    "audio",
}


def build_sudo_cmd(password: str, cmd: str) -> str:
    """Build a sudo command with proper password escaping.

    Uses printf instead of echo to avoid issues with special characters
    (single quotes, backslashes, etc.) in passwords.
    """
    escaped_password = shlex.quote(password)
    return f"printf '%s\\n' {escaped_password} | sudo -S {cmd}"


def _parse_svc_name(svc_file: str) -> str:
    """Extract service name from init script filename.

    S03node-red → node-red
    K92yolo11-detector → yolo11-detector
    """
    name = svc_file.lstrip("SK")
    while name and name[0].isdigit():
        name = name[1:]
    return name


def _is_system_service(svc_name: str) -> bool:
    """Check if a service name matches the system whitelist."""
    return any(svc_name.lower().startswith(wl) for wl in SYSTEM_SERVICES_WHITELIST)


async def exec_ssh_cmd(
    client,
    cmd: str,
    timeout: int = 30,
) -> Optional[str]:
    """Execute SSH command and return stdout."""
    try:
        stdin, stdout, stderr = await asyncio.to_thread(
            client.exec_command, cmd, timeout=timeout
        )
        stdout.channel.recv_exit_status()
        return stdout.read().decode()
    except Exception as e:
        logger.debug(f"Command failed: {e}")
        return None


async def stop_and_disable_nonystem_services(
    client,
    password: str,
    log_callback: Optional[Callable] = None,
) -> List[str]:
    """Stop and disable all non-system services (S* → K*).

    Returns list of disabled service names (for package removal).
    """
    disabled = []

    scan_script = 'for f in /etc/init.d/S*; do [ -f "$f" ] && basename "$f"; done'
    scan_cmd = (
        build_sudo_cmd(password, f"sh -c {shlex.quote(scan_script)}")
        + " 2>/dev/null || true"
    )
    result = await exec_ssh_cmd(client, scan_cmd)
    if not result:
        return disabled

    for svc_file in result.strip().split("\n"):
        svc_file = svc_file.strip()
        if not svc_file:
            continue

        svc_name = _parse_svc_name(svc_file)
        if not svc_name:
            continue

        if _is_system_service(svc_name):
            continue

        # Stop the service
        msg = f"Stopping non-system service: {svc_name}"
        logger.info(msg)
        if log_callback:
            await log_callback(msg)

        stop_cmd = build_sudo_cmd(
            password, f"/etc/init.d/{svc_file} stop 2>/dev/null || true"
        )
        await exec_ssh_cmd(client, stop_cmd)

        # Rename S* → K* to disable auto-start
        disable_cmd = build_sudo_cmd(
            password,
            f'mv /etc/init.d/{svc_file} /etc/init.d/$(echo {svc_file} | sed "s/^S/K/") 2>/dev/null || true',
        )
        await exec_ssh_cmd(client, disable_cmd)
        logger.info(f"Disabled: {svc_file} → K{svc_file[1:]}")

        disabled.append(svc_name)

    return disabled


async def remove_packages_for_services(
    client,
    password: str,
    service_names: List[str],
    log_callback: Optional[Callable] = None,
) -> None:
    """Remove opkg packages that match the given service names."""
    if not service_names:
        return

    cmd = "opkg list-installed 2>/dev/null || true"
    result = await exec_ssh_cmd(client, cmd)
    if not result:
        return

    for line in result.strip().split("\n"):
        parts = line.strip().split()
        if not parts:
            continue
        pkg_name = parts[0]
        pkg_lower = pkg_name.lower()

        for svc_name in service_names:
            if svc_name.lower() in pkg_lower:
                msg = f"Removing package: {pkg_name}"
                logger.info(msg)
                if log_callback:
                    await log_callback(msg)
                rm_cmd = build_sudo_cmd(
                    password, f"opkg remove {shlex.quote(pkg_name)} 2>/dev/null || true"
                )
                await exec_ssh_cmd(client, rm_cmd)
                break


async def remove_deployed_models(
    client,
    password: str,
    log_callback: Optional[Callable] = None,
) -> None:
    """Remove deployed models (NOT factory models)."""
    msg = "Removing deployed models"
    logger.info(msg)
    if log_callback:
        await log_callback(msg)
    cmd = build_sudo_cmd(
        password, "rm -rf /userdata/local/models/* 2>/dev/null || true"
    )
    await exec_ssh_cmd(client, cmd)


async def kill_nonystem_processes(
    client,
    password: str,
) -> None:
    """Kill remaining processes from disabled (K*) services."""
    scan_cmd = (
        build_sudo_cmd(
            password,
            'sh -c \'for f in /etc/init.d/K*; do [ -f "$f" ] && basename "$f"; done\'',
        )
        + " 2>/dev/null || true"
    )
    result = await exec_ssh_cmd(client, scan_cmd)
    if not result:
        return

    for svc_file in result.strip().split("\n"):
        svc_file = svc_file.strip()
        if not svc_file:
            continue

        svc_name = _parse_svc_name(svc_file)
        if not svc_name:
            continue

        # Skip Node-RED ecosystem
        if any(svc_name.lower().startswith(nr) for nr in NODERED_SERVICES):
            continue

        kill_cmd = build_sudo_cmd(
            password, f"killall {shlex.quote(svc_name)} 2>/dev/null || true"
        )
        await exec_ssh_cmd(client, kill_cmd)


async def restore_nodered_services(
    client,
    password: str,
) -> None:
    """Restore Node-RED services (K* → S*) and start them."""
    for svc_name in NODERED_SERVICES:
        restore_script = f"""for svc in /etc/init.d/K*{svc_name}*; do
    if [ -f "$svc" ]; then
        new_name=$(echo "$svc" | sed "s|/K|/S|")
        mv "$svc" "$new_name" 2>/dev/null && echo "Restored: $svc -> $new_name"
    fi
done"""
        restore_cmd = (
            build_sudo_cmd(password, f"sh -c {shlex.quote(restore_script)}")
            + " || true"
        )
        result = await exec_ssh_cmd(client, restore_cmd)
        if result and "Restored:" in result:
            logger.info(result.strip())


async def start_nodered_services(
    client,
    password: str,
) -> None:
    """Start all Node-RED ecosystem services."""
    for svc_name in NODERED_SERVICES:
        start_script = f"""for svc in /etc/init.d/S*{svc_name}*; do
    if [ -f "$svc" ]; then
        $svc start 2>/dev/null && echo "Started: $svc"
    fi
done"""
        cmd = (
            build_sudo_cmd(password, f"sh -c {shlex.quote(start_script)}")
            + " 2>/dev/null || true"
        )
        result = await exec_ssh_cmd(client, cmd)
        if result and "Started:" in result:
            logger.info(result.strip())


async def full_cleanup_and_restore(
    client,
    password: str,
    log_callback: Optional[Callable] = None,
) -> None:
    """Full reCamera cleanup: stop non-system services, remove packages/models,
    restore and start Node-RED ecosystem.

    Used by both deployer (pre-deploy) and restore manager (factory restore).
    """
    # 1. Stop and disable non-system services
    disabled = await stop_and_disable_nonystem_services(client, password, log_callback)

    # 2. Kill remaining processes
    await kill_nonystem_processes(client, password)

    # 3. Remove packages
    await remove_packages_for_services(client, password, disabled, log_callback)

    # 4. Remove deployed models
    await remove_deployed_models(client, password, log_callback)

    # 5. Restore Node-RED services (K* → S*)
    await restore_nodered_services(client, password)

    # 6. Start Node-RED services
    await start_nodered_services(client, password)
