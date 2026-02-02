This solution includes two feature sets that you can deploy as needed:

## Feature 1: Face Recognition (Steps 1-4)

Let Xiaozhi recognize your face and greet you automatically.

**Requirements**:
- SenseCAP Watcher
- USB-C data cable
- WiFi network

## Feature 2: Display Cast (Steps 5-6)

Cast Xiaozhi conversations to a large display.

**Requirements**:
- SenseCAP Watcher
- USB-C data cable
- Computer or Raspberry Pi with Docker
- HDMI display
- All devices on the same network

## Device Connection

After connecting Watcher to computer via USB-C, two serial ports will appear:

| Port Type | Purpose |
|-----------|---------|
| wchusbserial* | Flash Xiaozhi firmware |
| usbmodem* | Flash Face Recognition firmware |

## Skippable Steps

- If you only need face recognition, complete steps 1-4
- If you only need display, skip steps 1-4 and do steps 5-6 only

## Preset: Face Recognition {#face_recognition}

Add face recognition to your Xiaozhi, letting it recognize family and friends.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | AI voice assistant with camera |
| USB-C data cable | For firmware flashing |

**What you'll get:**
- Automatic greeting when recognized face appears
- Voice-based face enrollment ("Remember my face, I'm John")
- Stores up to 20 people

**Requirements:** WiFi network · [Xiaozhi App](https://github.com/78/xiaozhi-esp32) for device binding

## What You Need

| Item | Description |
|------|-------------|
| SenseCAP Watcher | Main device |
| USB-C data cable | For connecting to computer |
| WiFi network | Device needs internet |

## Connect Device

After connecting Watcher to computer via USB-C, two serial ports will appear:

| Port Type | Used For |
|-----------|----------|
| wchusbserial* | Xiaozhi firmware (Step 1) |
| usbmodem* | Face recognition firmware (Step 2) |

## After Deployment

Say "Remember my face, my name is John" to enroll. Next time you appear in front of the camera, Xiaozhi will greet you by name.

## Step 1: Flash Xiaozhi Firmware {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

### Connect Device

1. Connect Watcher to computer via USB-C cable
2. Select the serial port above (choose one starting with wchusbserial)
3. Click the Flash button

### After Flashing

Device will automatically restart. Xiaozhi face displayed on screen indicates success.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Flash Face Recognition Firmware {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

### Connect Device

1. Ensure Watcher is connected to computer
2. Select the serial port above (choose one starting with usbmodem)
3. Click the Flash button

### Enter Flash Mode

After clicking Flash, you need to press the reset button on the device to enter flash mode.

### After Flashing

Device will automatically restart. Face recognition is now enabled.

### Troubleshooting

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

---

## Step 3: Configure Xiaozhi {#face_configure type=manual required=false}

### Connect to WiFi

Device will prompt for network setup on first boot. Follow voice instructions to connect to WiFi.

### Bind Xiaozhi Account

1. Open Xiaozhi App
2. Scan the QR code displayed on device
3. Complete the binding process

### Test the Function

Wake up the device by saying "Xiaozhi Xiaozhi", then say "Remember my face, my name is Mike" to test face enrollment.

---

## Step 4: Face Enrollment Guide {#face_enrollment type=manual required=false}

### Enroll a Face

1. Wake up Xiaozhi: "Xiaozhi Xiaozhi"
2. Say: "Remember my face, my name is **your name**"
3. Face the camera directly with good lighting
4. Wait for "Enrollment successful" confirmation

### Test Recognition

1. Leave the camera view
2. Reappear in front of the camera
3. Device will say "Detected **your name**"

### Manage Faces

| Action | Voice Command |
|--------|---------------|
| List enrolled people | "Who do you know" |
| Delete someone | "Delete Mike's face" |

### Notes

- Name is required when enrolling
- Poor lighting affects recognition
- Maximum 20 people can be stored

---

## Preset: Display Cast {#display_cast}

Cast Xiaozhi conversations to TV or large display, ideal for exhibition halls, meeting rooms and multi-person scenarios.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | AI voice assistant |
| Computer/Raspberry Pi | Runs display service (Docker required) |
| HDMI Display | Shows cast content |

**What you'll get:**
- Real-time conversation display on big screen
- Fullscreen mode for presentations
- Works over local network

**Requirements:** All devices on same network · Docker installed

## What You Need

| Item | Description |
|------|-------------|
| SenseCAP Watcher | Voice assistant device |
| USB-C data cable | For flashing firmware |
| Computer or Raspberry Pi | With Docker installed, runs display service |
| HDMI display | Shows the cast content |
| Local network | All devices on same network |

## Deployment Flow

1. Flash Watcher display firmware
2. Deploy display service on computer/Raspberry Pi

## After Deployment

- Open `http://<device-ip>:8765` on your display
- Press `F` to enter fullscreen mode
- Talk to Watcher - conversations appear on the big screen

## Step 1: Flash Watcher Firmware {#display_watcher type=esp32_usb required=true config=devices/display_watcher.yaml}

### Connect Device

1. Connect Watcher to your computer using USB-C cable
2. Select the serial port above
3. If not detected, try a different USB port or cable

---

## Step 2: Deploy Display Service {#display_service type=docker_deploy required=true config=devices/display_local.yaml}

### Target: Local Deployment {#display_service_local type=local config=devices/display_local.yaml default=true}

Deploy the display service on your local computer.

### Prerequisites

- Docker Desktop installed and running
- Port 8765 available

### After Deployment

1. Open `http://localhost:8765` in browser
2. Press `F` to enter fullscreen mode
3. Wake up Watcher and say "Open settings"
4. Find "Display Address" and say the server address (e.g., `your-ip:8765`)

![Wiring](gallery/architecture.svg)

### Target: Remote Deployment {#display_service_remote type=remote config=devices/recomputer.yaml}

Deploy the display service to a remote device (reComputer, Raspberry Pi, etc.).

### Before You Begin

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)

### After Deployment

1. Open `http://<device-ip>:8765` on display device browser
2. Press `F` to enter fullscreen mode
3. Wake up Watcher and say "Open settings"
4. Find "Display Address" and say the server address (e.g., `192.168.1.100:8765`)

![Wiring](gallery/architecture.svg)

---

# Deployment Complete

## Deployment Complete!

Your Smart Space AI Assistant is now ready.

### Face Recognition Feature

**How to Test**:
- Say "Remember my face, my name is John" to enroll
- Next time you appear in front of the camera, Xiaozhi will greet you

**Voice Commands**:
- Enroll: "Remember my face, my name is [name]"
- Delete: "Delete [name]'s face"
- Query: "Who do you know"

### Display Cast Feature

**How to Test**:
1. Navigate to `http://<device-ip>:8765` on your display
2. Press `F` to enter fullscreen mode
3. Talk to Watcher - conversations appear on the big screen

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Face recognition not working | Ensure sufficient lighting, face the camera directly |
| No audio on display | Check HDMI audio settings |
| Watcher not connecting to display | Verify all devices on same network |
