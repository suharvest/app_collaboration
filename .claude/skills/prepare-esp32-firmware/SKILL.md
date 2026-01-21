---
name: prepare-esp32-firmware
description: Prepare ESP32 firmware files for solution deployment. Use when setting up firmware flashing, configuring esptool parameters, or adding ESP32/ESP32-S3/ESP32-C3 device support to a solution.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare ESP32 Firmware

Guide for preparing ESP32 device firmware and configuration files.

## Required Files

| File | Description | Required |
|------|-------------|----------|
| `firmware.bin` | Main firmware binary | Yes |
| `bootloader.bin` | Bootloader (first flash) | Optional |
| `partition-table.bin` | Partition table | Optional |

## Directory Structure

```
solutions/[solution_id]/
├── assets/
│   └── watcher_firmware/      # or device name
│       ├── firmware.bin
│       ├── bootloader.bin     # optional
│       └── partition-table.bin # optional
└── devices/
    └── [device_id].yaml       # device config
```

## Device Configuration Template

Create `devices/[device_id].yaml`:

```yaml
version: "1.0"
id: watcher
name: SenseCAP Watcher
name_zh: SenseCAP Watcher
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x10c4"      # actual VID
  usb_product_id: "0xea60"     # actual PID
  fallback_ports:
    - /dev/ttyUSB*
    - /dev/ttyACM*

firmware:
  source:
    type: local
    path: assets/watcher_firmware/firmware.bin

  flash_config:
    chip: esp32s3              # esp32/esp32s2/esp32s3/esp32c3
    baud_rate: 921600
    flash_mode: dio
    flash_freq: 80m
    flash_size: 16MB
    partitions:
      - name: app
        offset: "0x10000"
        file: firmware.bin

steps:
  - id: detect
    name: Detect Device
    name_zh: 检测设备
    optional: false
    default: true

  - id: erase
    name: Erase Flash (Optional)
    name_zh: 擦除闪存 (可选)
    optional: true
    default: false

  - id: flash
    name: Flash Firmware
    name_zh: 烧录固件
    optional: false
    default: true

  - id: verify
    name: Verify
    name_zh: 验证
    optional: false
    default: true

post_deployment:
  reset_device: true
  wait_for_ready: 5
```

## Common Chip Configurations

### ESP32-S3 (SenseCAP Watcher)
```yaml
chip: esp32s3
baud_rate: 921600
flash_mode: dio
flash_freq: 80m
flash_size: 16MB
```

### ESP32-C3 (XIAO)
```yaml
chip: esp32c3
baud_rate: 460800
flash_mode: dio
flash_freq: 40m
flash_size: 4MB
```

### ESP32 (Classic)
```yaml
chip: esp32
baud_rate: 460800
flash_mode: dio
flash_freq: 40m
flash_size: 4MB
```

## Common USB VID/PID

| Device | VID | PID |
|--------|-----|-----|
| CP210x (Watcher) | 0x10c4 | 0xea60 |
| CH340 | 0x1a86 | 0x7523 |
| FTDI | 0x0403 | 0x6001 |
| ESP32-S3 USB | 0x303a | 0x1001 |

## Get USB VID/PID

```bash
# Linux/macOS
lsusb
# macOS
system_profiler SPUSBDataType
```

## Update solution.yaml

Add device reference:

```yaml
deployment:
  devices:
    - id: watcher
      name: SenseCAP Watcher
      type: esp32_usb
      config_file: devices/watcher.yaml
      section:
        title: Flash Firmware
        title_zh: 烧录固件
        description_file: deploy/sections/watcher.md
        description_file_zh: deploy/sections/watcher_zh.md
```

## Manual Test

```bash
esptool.py --port /dev/ttyUSB0 --chip esp32s3 \
  --baud 921600 write_flash \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x10000 firmware.bin
```
