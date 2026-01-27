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
