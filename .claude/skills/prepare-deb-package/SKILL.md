---
name: prepare-deb-package
description: Build Debian package for Provisioning Station. Use when packaging the application as .deb, configuring systemd service, creating desktop shortcuts, or setting up debian control files.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare Deb Package

Guide for packaging Provisioning Station as a Debian installation package.

## Target Installation Structure

```
/opt/provisioning-station/
├── provisioning_station/     # Backend Python code
├── frontend/dist/            # Frontend build
├── solutions/                # Solution configs
├── .venv/                    # Python venv (bundled)
├── data/                     # Runtime data
│   ├── cache/
│   └── logs/
└── run.sh

/etc/systemd/system/
└── provisioning-station.service

/usr/share/applications/
└── provisioning-station.desktop
```

## Debian Directory Structure

```
debian/
├── control                   # Package metadata
├── changelog                 # Version history
├── rules                     # Build rules
├── compat                    # debhelper level
├── postinst                  # Post-install script
├── prerm                     # Pre-remove script
├── postrm                    # Post-remove script
├── provisioning-station.service    # systemd unit
└── provisioning-station.desktop    # Desktop entry
```

## debian/control

```
Source: provisioning-station
Section: utils
Priority: optional
Maintainer: Seeed Studio <support@seeed.cc>
Build-Depends: debhelper (>= 12)
Standards-Version: 4.5.0

Package: provisioning-station
Architecture: arm64
Depends: docker.io | docker-ce,
         docker-compose-v2 | docker-compose-plugin,
         python3 (>= 3.10),
         libusb-1.0-0,
         ${misc:Depends}
Recommends: chromium-browser | firefox-esr
Description: SenseCraft Solution Deployment Tool
 IoT solution deployment platform for Seeed Studio hardware.
```

## debian/changelog

```
provisioning-station (1.0.0) stable; urgency=medium

  * Initial release

 -- Seeed Studio <support@seeed.cc>  Tue, 07 Jan 2025 10:00:00 +0800
```

## debian/compat

```
12
```

## debian/postinst

```bash
#!/bin/bash
set -e

case "$1" in
    configure)
        chmod +x /opt/provisioning-station/run.sh

        # Add user to dialout group (serial port)
        if [ -n "$SUDO_USER" ]; then
            usermod -aG dialout "$SUDO_USER" 2>/dev/null || true
            usermod -aG docker "$SUDO_USER" 2>/dev/null || true
        fi

        systemctl daemon-reload
        systemctl enable provisioning-station.service
        systemctl start provisioning-station.service

        echo "Provisioning Station installed!"
        echo "Access: http://127.0.0.1:3260"
        ;;
esac
exit 0
```

## debian/prerm

```bash
#!/bin/bash
set -e

case "$1" in
    remove|upgrade|deconfigure)
        systemctl stop provisioning-station.service 2>/dev/null || true
        systemctl disable provisioning-station.service 2>/dev/null || true
        ;;
esac
exit 0
```

## debian/postrm

```bash
#!/bin/bash
set -e

case "$1" in
    purge)
        rm -rf /opt/provisioning-station/data
        ;;
esac
exit 0
```

## debian/provisioning-station.service

```ini
[Unit]
Description=Provisioning Station Service
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/provisioning-station
Environment="PATH=/opt/provisioning-station/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/provisioning-station/.venv/bin/python -m uvicorn provisioning_station.main:app --host 127.0.0.1 --port 3260
Restart=on-failure
RestartSec=5
StandardOutput=append:/opt/provisioning-station/data/logs/service.log
StandardError=append:/opt/provisioning-station/data/logs/service.log

[Install]
WantedBy=multi-user.target
```

## debian/provisioning-station.desktop

```ini
[Desktop Entry]
Version=1.0
Type=Application
Name=Provisioning Station
Name[zh_CN]=部署工作站
Comment=IoT Solution Deployment Tool
Exec=xdg-open http://127.0.0.1:3260
Icon=/opt/provisioning-station/frontend/dist/assets/icon.png
Terminal=false
Categories=Development;Utility;
StartupNotify=true
```

## Build Steps

### 1. Setup Build Environment (arm64)

```bash
sudo apt install build-essential devscripts debhelper
curl -LsSf https://astral.sh/uv/install.sh | sh
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs
```

### 2. Build Frontend

```bash
cd frontend && npm ci && npm run build
```

### 3. Create Python venv

```bash
uv venv .venv
uv pip install -p .venv -r requirements.txt
```

### 4. Build Package

```bash
dpkg-buildpackage -us -uc -b
```

### 5. Test Installation

```bash
sudo dpkg -i provisioning-station_1.0.0_arm64.deb
sudo apt install -f  # fix dependencies
systemctl status provisioning-station
```

## Cross-compile with Docker

```bash
docker run --rm --platform linux/arm64 \
  -v $(pwd):/src \
  arm64v8/debian:bookworm \
  bash -c "cd /src && dpkg-buildpackage -us -uc -b"
```

## Version Update Checklist

1. `debian/changelog` - Add version entry
2. `pyproject.toml` - Update version
3. `frontend/package.json` - Update version

```bash
dch -i  # increment version
dch -v 2.0.0  # specific version
```

## Verification Checklist

- [ ] Package installs on clean system
- [ ] systemd service starts automatically
- [ ] Web UI accessible at 127.0.0.1:3260
- [ ] Desktop shortcut works
- [ ] Serial port accessible (dialout group)
- [ ] Docker commands work (docker group)
- [ ] Service stops on uninstall
- [ ] Data cleaned on purge
