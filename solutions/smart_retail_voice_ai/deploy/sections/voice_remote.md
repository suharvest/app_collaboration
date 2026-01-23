# Remote Deployment

Deploy voice services to a remote device (reRouter, Raspberry Pi, etc.).

## Before You Begin

1. **Connect target device to the network**
   - Ensure the device is on the same network as your computer
   - Note down the device's IP address (default: 192.168.49.1 for OpenWrt)

2. **Get device credentials**
   - SSH username (usually `root` for OpenWrt)
   - SSH password (empty by default on OpenWrt)

## Connection Settings

Enter the following information:

| Field | Description | Example |
|-------|-------------|---------|
| Device IP | Target device IP address | 192.168.49.1 |
| SSH Password | Login password (optional) | your-password |

## After Deployment

1. SSH and run `docker ps` to verify three containers are running
2. Visit `http://192.168.49.1:8090` to open edge client
3. Start real-time voice transcription testing
