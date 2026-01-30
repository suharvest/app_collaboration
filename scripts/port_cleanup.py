#!/usr/bin/env python3
"""
Cross-platform port cleanup utility.

Detects and optionally kills processes occupying specified ports,
but only if they appear to be leftover processes from this application.
"""

import argparse
import platform
import re
import subprocess
import sys
from typing import NamedTuple

import psutil


class PortProcess(NamedTuple):
    """Information about a process using a port."""

    pid: int
    name: str
    cmdline: str
    port: int


# Keywords that identify this application's processes
OUR_PROCESS_KEYWORDS = [
    "provisioning_station",
    "provisioning-station",
    "uvicorn",
    "vite",
    "npm run dev",
    "node_modules/.bin/vite",
    "sensecraft",
]


def find_process_on_port(port: int) -> PortProcess | None:
    """Find the process using a specific port (cross-platform)."""
    system = platform.system()

    try:
        if system == "Darwin":
            # macOS: use lsof
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-n", "-P"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None

            # Parse lsof output (skip header)
            for line in result.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    pid = int(parts[1])
                    return _get_process_info(pid, port)

        elif system == "Linux":
            # Linux: use ss or lsof
            result = subprocess.run(
                ["ss", "-tlnp", f"sport = :{port}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                # Parse ss output to find PID
                # Format: LISTEN 0 128 0.0.0.0:3260 0.0.0.0:* users:(("python",pid=12345,fd=6))
                match = re.search(r"pid=(\d+)", result.stdout)
                if match:
                    pid = int(match.group(1))
                    return _get_process_info(pid, port)

            # Fallback to lsof if ss doesn't work
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-sTCP:LISTEN", "-n", "-P"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n")[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        pid = int(parts[1])
                        return _get_process_info(pid, port)

        elif system == "Windows":
            # Windows: use netstat
            result = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    # Look for LISTENING on our port
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        if parts:
                            pid = int(parts[-1])
                            return _get_process_info(pid, port)

    except (subprocess.SubprocessError, ValueError, OSError) as e:
        print(f"  Warning: Error checking port {port}: {e}", file=sys.stderr)

    return None


def _get_process_info(pid: int, port: int) -> PortProcess | None:
    """Get process information by PID."""
    try:
        proc = psutil.Process(pid)
        cmdline = " ".join(proc.cmdline())
        return PortProcess(
            pid=pid,
            name=proc.name(),
            cmdline=cmdline,
            port=port,
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def is_our_process(proc: PortProcess) -> bool:
    """Check if a process appears to be from our application."""
    search_text = f"{proc.name} {proc.cmdline}".lower()
    return any(keyword.lower() in search_text for keyword in OUR_PROCESS_KEYWORDS)


def kill_process(proc: PortProcess, force: bool = False) -> bool:
    """Kill a process and its children."""
    try:
        process = psutil.Process(proc.pid)

        # Kill children first
        children = process.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except psutil.NoSuchProcess:
                pass

        # Then kill the parent
        process.terminate()

        # Wait for graceful termination
        gone, alive = psutil.wait_procs([process] + children, timeout=3)

        # Force kill if still alive
        if alive and force:
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass

        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"  Failed to kill process {proc.pid}: {e}", file=sys.stderr)
        return False


def cleanup_port(port: int, auto_kill: bool = True, verbose: bool = True) -> bool:
    """
    Check and cleanup a port.

    Returns:
        True if port is now available, False otherwise.
    """
    proc = find_process_on_port(port)

    if proc is None:
        if verbose:
            print(f"  Port {port}: Available")
        return True

    if verbose:
        print(f"  Port {port}: In use by PID {proc.pid} ({proc.name})")
        cmdline_display = proc.cmdline[:80] + ("..." if len(proc.cmdline) > 80 else "")
        print(f"    Command: {cmdline_display}")

    if is_our_process(proc):
        if verbose:
            print("    -> Detected as leftover process from this application")

        if auto_kill:
            if verbose:
                print(f"    -> Terminating process {proc.pid}...")
            if kill_process(proc, force=True):
                if verbose:
                    print("    -> Successfully terminated")
                return True
            else:
                if verbose:
                    print("    -> Failed to terminate", file=sys.stderr)
                return False
        else:
            if verbose:
                print("    -> Skipping (auto-kill disabled)")
            return False
    else:
        if verbose:
            print("    -> NOT a leftover process, will not terminate automatically")
            print("    -> Please close this application manually or use a different port")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup ports by killing leftover processes from this application"
    )
    parser.add_argument(
        "ports",
        type=int,
        nargs="+",
        help="Port numbers to check and cleanup",
    )
    parser.add_argument(
        "--no-kill",
        action="store_true",
        help="Only check, don't kill processes",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output errors",
    )
    parser.add_argument(
        "--exit-on-blocked",
        action="store_true",
        help="Exit with error code if any port is blocked by non-application process",
    )

    args = parser.parse_args()

    if not args.quiet:
        print("Checking ports...")

    all_available = True
    blocked_by_other = False

    for port in args.ports:
        proc = find_process_on_port(port)
        if proc and not is_our_process(proc):
            blocked_by_other = True

        available = cleanup_port(
            port,
            auto_kill=not args.no_kill,
            verbose=not args.quiet,
        )
        if not available:
            all_available = False

    if not args.quiet:
        print()

    if args.exit_on_blocked and blocked_by_other:
        sys.exit(2)  # Port blocked by other application

    if not all_available:
        sys.exit(1)  # Some ports still not available

    sys.exit(0)


if __name__ == "__main__":
    main()
