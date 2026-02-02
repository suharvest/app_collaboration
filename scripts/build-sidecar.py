#!/usr/bin/env python3
"""
Build script for provisioning-station sidecar
Builds the Python backend as a standalone executable using PyInstaller

Usage:
    python scripts/build-sidecar.py [--target TARGET_TRIPLE]

Examples:
    python scripts/build-sidecar.py
    python scripts/build-sidecar.py --target x86_64-unknown-linux-gnu
    python scripts/build-sidecar.py --target x86_64-pc-windows-msvc
    python scripts/build-sidecar.py --target aarch64-apple-darwin
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def get_target_triple() -> str:
    """Determine the current platform's target triple for Tauri."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == 'darwin':
        if machine == 'arm64':
            return 'aarch64-apple-darwin'
        return 'x86_64-apple-darwin'
    elif system == 'linux':
        if machine == 'aarch64':
            return 'aarch64-unknown-linux-gnu'
        return 'x86_64-unknown-linux-gnu'
    elif system == 'windows':
        if machine == 'arm64':
            return 'aarch64-pc-windows-msvc'
        return 'x86_64-pc-windows-msvc'
    else:
        raise RuntimeError(f"Unsupported platform: {system}/{machine}")


def main():
    parser = argparse.ArgumentParser(description='Build provisioning-station sidecar')
    parser.add_argument(
        '--target',
        type=str,
        default=None,
        help='Target triple (e.g., x86_64-unknown-linux-gnu). Auto-detected if not specified.'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean build artifacts before building'
    )
    args = parser.parse_args()

    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    spec_file = project_root / 'pyinstaller' / 'provisioning-station.spec'
    dist_dir = project_root / 'pyinstaller' / 'dist'
    build_dir = project_root / 'pyinstaller' / 'build'
    binaries_dir = project_root / 'src-tauri' / 'binaries'

    # Ensure spec file exists
    if not spec_file.exists():
        print(f"Error: Spec file not found: {spec_file}")
        sys.exit(1)

    # Determine target triple
    target = args.target or get_target_triple()
    print(f"Building for target: {target}")

    # Clean if requested
    if args.clean:
        print("Cleaning build artifacts...")
        for d in [dist_dir, build_dir]:
            if d.exists():
                shutil.rmtree(d)

    # Ensure binaries directory exists
    binaries_dir.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller
    print("Running PyInstaller...")
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--distpath', str(dist_dir),
        '--workpath', str(build_dir),
        '--noconfirm',
        str(spec_file)
    ]

    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root)

    result = subprocess.run(cmd, env=env, cwd=str(project_root))
    if result.returncode != 0:
        print("Error: PyInstaller build failed")
        sys.exit(1)

    # Find the built executable (onedir mode creates a directory)
    system = platform.system().lower()
    if system == 'windows':
        exe_name = 'provisioning-station-bin.exe'  # Temp name from spec
    else:
        exe_name = 'provisioning-station-bin'  # Temp name from spec

    # onedir mode creates: dist/provisioning-station/provisioning-station-bin[.exe]
    built_dir = dist_dir / 'provisioning-station'
    built_exe = built_dir / exe_name
    built_internal = built_dir / '_internal'

    if not built_exe.exists():
        print(f"Error: Built executable not found: {built_exe}")
        sys.exit(1)

    if not built_internal.exists():
        print(f"Error: _internal directory not found: {built_internal}")
        sys.exit(1)

    # Rename for Tauri sidecar format
    # Tauri expects: binaries/NAME-TARGET_TRIPLE[.exe]
    if system == 'windows':
        sidecar_name = f'provisioning-station-{target}.exe'
    else:
        sidecar_name = f'provisioning-station-{target}'

    sidecar_path = binaries_dir / sidecar_name

    # Copy the executable
    print(f"Copying executable to: {sidecar_path}")
    shutil.copy2(built_exe, sidecar_path)

    # Copy the _internal directory
    internal_dest = binaries_dir / '_internal'
    if internal_dest.exists():
        print(f"Removing existing _internal directory...")
        shutil.rmtree(internal_dest)
    print(f"Copying _internal to: {internal_dest}")
    shutil.copytree(built_internal, internal_dest)

    # Make executable on Unix systems
    if system != 'windows':
        os.chmod(sidecar_path, 0o755)
        # Also set execute permission on .so/.dylib files in _internal
        for ext in ['*.so', '*.so.*', '*.dylib']:
            for lib_file in internal_dest.rglob(ext):
                os.chmod(lib_file, 0o755)

    # Calculate total size
    total_size = sidecar_path.stat().st_size
    for f in internal_dest.rglob('*'):
        if f.is_file():
            total_size += f.stat().st_size

    print(f"\nSidecar built successfully!")
    print(f"  Executable: {sidecar_path}")
    print(f"  Internal dir: {internal_dest}")
    print(f"  Total size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == '__main__':
    main()
