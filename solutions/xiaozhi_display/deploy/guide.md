## Deployment Overview

This solution requires two deployment steps:

1. **Flash Watcher Firmware** - Program the Watcher with display-enabled firmware
2. **Deploy Display Service** - Run the display server on reComputer/Raspberry Pi

## Prerequisites

Before starting deployment:

- [ ] SenseCAP Watcher with USB-C cable
- [ ] reComputer or Raspberry Pi with Docker installed
- [ ] HDMI display connected to the computing device
- [ ] All devices on the same network

## After Deployment

Once both steps are complete:

1. Open browser on the display device and navigate to `http://localhost:8765`
2. Use keyboard shortcut `F` or `F11` to enter fullscreen mode
3. Configure Watcher to connect to the display server IP address
4. Start a conversation - content will appear on the large screen!
