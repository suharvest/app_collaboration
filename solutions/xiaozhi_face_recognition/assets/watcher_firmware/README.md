# Watcher Firmware Files

Place the following firmware files in this directory:

## Required Files

1. **xiaozhi_firmware.bin** - Xiaozhi ESP32-S3 firmware
   - Source: https://github.com/78/xiaozhi-esp32
   - For flashing to ESP32-S3 via wchusbserial port

2. **face_recognition.img** - Himax WE2 face recognition firmware
   - Source: SSCMA (Seeed SenseCraft Model Assistant)
   - For flashing to Himax WE2 via usbmodem port

## How to Obtain

### Xiaozhi Firmware
```bash
# Clone the repository
git clone https://github.com/78/xiaozhi-esp32.git

# Build or download pre-built firmware
# Copy firmware.bin to this directory as xiaozhi_firmware.bin
```

### Face Recognition Firmware
The face recognition model can be obtained from SSCMA:
- Visit: https://sensecraft.seeed.cc/
- Select face recognition model for Himax WE2
- Download and place as face_recognition.img
