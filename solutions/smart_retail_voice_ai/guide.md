This solution deploys a complete edge-based voice AI system for retail environments.

## Prerequisites

- reRouter CM4 with at least 4GB RAM and 32GB storage
- reSpeaker XVF3800 4-mic array
- USB-C cable for reSpeaker configuration
- Network cable for reRouter connection

## Preset: Standard Deployment {#default}

## Step 1: Flash OpenWrt Firmware {#firmware type=manual required=true config=devices/firmware.yaml}

### Flash Firmware

1. Download: [Global](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-global.img.gz) | [China](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-cn.img.gz)
2. Flash to reRouter using Raspberry Pi Imager
3. Connect WAN to router, LAN to computer
4. Visit `http://192.168.49.1`, login with root (empty password)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot access 192.168.49.1 | Make sure the cable is plugged into the LAN port, not the WAN port |
| Page loads slowly | Wait 2 minutes for the system to fully boot |
| Flashing failed | Format the storage device and try again |
| Login failed | Password is empty, just click login |

---

## Step 2: Configure reSpeaker {#respeaker type=manual required=true config=devices/respeaker.yaml}

### Configure Microphone Array

1. Connect reSpeaker XVF3800 via USB to **your computer** (not reRouter)
2. Clone repo: `git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git`
3. Navigate to your OS folder and run:
   ```bash
   sudo ./xvf_host clear_configuration 1
   sudo ./xvf_host audio_mgr_op_r 8 0
   sudo ./xvf_host save_configuration 1
   ```
4. Disconnect from computer, connect reSpeaker to **reRouter USB port**

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Device not recognized | Try a different USB cable, make sure it's a data cable not just a charging cable |
| Command error | Make sure you're in the correct OS directory |
| Permission denied | Mac/Linux requires sudo, Windows needs to run as administrator |
| No effect after configuration | Unplug and replug reSpeaker to apply the configuration |

---

## Step 3: Deploy Voice Services {#voice_services type=docker_deploy required=true config=devices/rerouter.yaml}

### Target: Local Deployment {#voice_services_local config=devices/voice_local.yaml}

## Local Deployment

Deploy voice services on your local computer.

### Requirements

- Docker Desktop installed and running
- reSpeaker XVF3800 connected via USB
- At least 2GB free disk space
- Port 8090 available

### After Deployment

1. Run `docker ps` to verify containers are running
2. Open `http://localhost:8090` to access edge client
3. Start real-time voice transcription testing

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | Start the Docker Desktop application |
| Port 8090 is occupied | Close the program using that port, or modify the configuration to use a different port |
| Microphone device not found | Unplug and replug USB, verify it appears in Device Manager |
| Container startup failed | Check Docker logs: `docker logs <container_name>` |

### Target: Remote Deployment {#voice_services_remote config=devices/rerouter.yaml default=true}

## Remote Deployment

Deploy voice services to a remote device (reRouter, Raspberry Pi, etc.).

### Before You Begin

1. **Connect target device to the network**
   - Ensure the device is on the same network as your computer
   - Note down the device's IP address (default: 192.168.49.1 for OpenWrt)

2. **Get device credentials**
   - SSH username (usually `root` for OpenWrt)
   - SSH password (empty by default on OpenWrt)

### Connection Settings

Enter the following information:

| Field | Description | Example |
|-------|-------------|---------|
| Device IP | Target device IP address | 192.168.49.1 |
| SSH Password | Login password (optional) | your-password |

### After Deployment

1. SSH and run `docker ps` to verify three containers are running
2. Visit `http://192.168.49.1:8090` to open edge client
3. Start real-time voice transcription testing

![Wiring](intro/gallery/wan_lan.png)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection refused | Make sure the cable is plugged into the LAN port and the IP is correct |
| Authentication failed | OpenWrt default password is empty, just press Enter |
| Image download timeout | Check the WAN port network connection, make sure you can access the internet |
| Container startup failed | SSH in and run `docker logs` to view error messages |
| Microphone not found | Run `arecord -l` to verify reSpeaker is recognized |

---

# Deployment Complete

## Deployment Successful!

The Smart Retail Voice AI solution has been deployed successfully.

### Next Steps

1. **Reboot the device** - Strongly recommended to ensure all settings take effect:
   ```bash
   reboot
   ```

2. **Access the Voice Client** - After reboot, navigate to:
   - http://192.168.49.1:8090

3. **Test Voice Recognition** - Speak near the reSpeaker and verify transcription appears in real-time

4. **Configure Cloud Platform** (Optional) - Connect to SenseCraft Voice cloud platform for:
   - Multi-store management
   - AI-powered analytics
   - Keyword hotspot analysis

### Troubleshooting

If services are not working:

```bash
# Check container status
docker ps

# View voice client logs
docker logs sensecraft-voice-client

# Check audio devices
ls -l /dev/snd/
```
