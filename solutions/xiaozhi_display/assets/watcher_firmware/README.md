# Watcher Firmware for Display Cast

This directory contains the pre-built firmware for SenseCAP Watcher with remote display functionality.

## Firmware Version

- **Version**: 16c9887 (feat: remote-display with mDNS auto-discovery)
- **Target**: ESP32-S3
- **Flash Size**: 16MB
- **Build Date**: 2026-01-21

## Features

This firmware adds the following features to the standard Xiaozhi firmware:

1. **Remote Display Client**
   - WebSocket connection to display server
   - UI state broadcasting (emotions, text, chat messages)

2. **mDNS Discovery**
   - Auto-discovers display servers on the network
   - Service type: `_xiaozhi-display._tcp.local`

3. **Audio Streaming**
   - Opus encoded audio sent to display server
   - Server decodes and plays through HDMI

## Building from Source

If you need to build the firmware yourself:

```bash
cd /path/to/xiaozhi-esp32

# Set up ESP-IDF environment
export IDF_PYTHON_ENV_PATH=/Users/harvest/.espressif/python_env/idf5.5_py3.14_env
source /path/to/esp-idf/export.sh

# Configure and build
idf.py set-target esp32s3
idf.py menuconfig  # Select SenseCAP Watcher board
idf.py build

# Generate merged binary
idf.py merge-bin

# Output: build/merged-binary.bin
```

## Configuration

After flashing, configure the display server address:

1. Open Watcher settings
2. Navigate to Remote Display
3. Enter server URL: `ws://<server-ip>:8765`

Or rely on mDNS auto-discovery if both devices are on the same network.

## Flashing

The firmware can be flashed using:

1. **SenseCraft Solution Platform** (recommended)
   - Use the deploy page for one-click flashing

2. **esptool (manual)**
   ```bash
   esptool.py --chip esp32s3 --port /dev/ttyUSB0 \
     --baud 921600 write_flash 0x0 firmware.bin
   ```
