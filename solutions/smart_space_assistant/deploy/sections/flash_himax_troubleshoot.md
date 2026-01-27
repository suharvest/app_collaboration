### Having Issues?

| Problem | Solution |
|---------|----------|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | See "Device keeps restarting" below |

### Device Keeps Restarting During Flash (SenseCAP Watcher)

**Symptom**: Flashing appears to work but fails near completion, or device restarts multiple times during flash.

**Cause**: SenseCAP Watcher's ESP32 firmware monitors the Himax chip. When Himax enters download mode, ESP32 detects this as an "anomaly" and resets Himax, interrupting the flash process.

**Automatic Fix**: This app automatically holds ESP32 in reset while flashing Himax. If auto-detection fails, try:

1. Ensure both USB ports are detected (usbmodem and wchusbserial)
2. Close any other applications using the serial ports
3. Reconnect the USB cable

**Manual Fix**: If automatic protection doesn't work:
1. Open a Python terminal
2. Hold ESP32 in reset: `import serial; s=serial.Serial('/dev/cu.wchusbserial*', 115200); s.dtr=False`
3. Flash Himax in another terminal
4. Close the Python terminal to release ESP32

> **Note**: This issue only affects SenseCAP Watcher, not standalone Grove Vision AI V2.
