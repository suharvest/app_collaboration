# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for provisioning-station sidecar
Builds a single executable for Tauri desktop application
"""

import sys
import os
from pathlib import Path

# Project root directory
project_root = Path(SPECPATH).parent
provisioning_dir = project_root / 'provisioning_station'

# Determine platform-specific settings
if sys.platform == 'win32':
    icon_file = str(project_root / 'src-tauri' / 'icons' / 'icon.ico')
    exe_name = 'provisioning-station.exe'
elif sys.platform == 'darwin':
    icon_file = str(project_root / 'src-tauri' / 'icons' / 'icon.icns')
    exe_name = 'provisioning-station'
else:
    icon_file = None
    exe_name = 'provisioning-station'

# Hidden imports required by the application
hiddenimports = [
    # Main application package
    'provisioning_station',
    'provisioning_station.main',
    'provisioning_station.config',
    'provisioning_station.routers',
    'provisioning_station.services',
    'provisioning_station.models',

    # FastAPI / Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.config',
    'uvicorn.main',

    # FastAPI
    'fastapi',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',

    # Pydantic
    'pydantic',
    'pydantic.json_schema',
    'pydantic_settings',

    # YAML processing
    'yaml',

    # Markdown
    'markdown',
    'markdown.extensions',
    'markdown.extensions.tables',
    'markdown.extensions.fenced_code',

    # Serial/USB
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
    'serial.tools.list_ports_common',
    'serial.tools.list_ports_windows',  # Windows COM port detection
    'serial.tools.list_ports_linux',
    'serial.tools.list_ports_osx',
    'serial.win32',  # Windows serial port support
    'esptool',
    'xmodem',  # Himax flashing fallback

    # SSH/SCP
    'paramiko',
    'scp',

    # Docker
    'docker',
    'docker.api',
    'docker.models',
    'docker.transport',

    # MQTT
    'paho.mqtt',
    'paho.mqtt.client',

    # HTTP
    'httpx',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',

    # Other
    'dotenv',
    'multipart',
    'python_multipart',
    'websockets',
]

# Collect data files
# NOTE: solutions directory is NOT bundled here - it's bundled by Tauri as external resources
# The sidecar will find solutions via SOLUTIONS_DIR env var or relative path
datas = []

# Collect packages that need their data files
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect esptool data files (stub flasher JSON files are required)
datas += collect_data_files('esptool')

# Collect all submodules for packages that have dynamic imports
hiddenimports += collect_submodules('esptool')
hiddenimports += collect_submodules('uvicorn')

# Analysis
a = Analysis(
    [str(provisioning_dir / '__main__.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Executable (onedir mode - faster startup)
# Note: EXE name must differ from COLLECT name to avoid path conflicts
exe = EXE(
    pyz,
    a.scripts,
    [],  # Don't include binaries/zipfiles/datas in EXE for onedir mode
    name=exe_name.replace('.exe', '') + '-bin',  # Temp name, COLLECT will place in final dir
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide console window (Tauri captures stdout/stderr)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file if icon_file and os.path.exists(icon_file) else None,
)

# Collect all files into a directory (onedir mode)
# The executable inside will be named 'provisioning-station-bin'
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='provisioning-station',
)
