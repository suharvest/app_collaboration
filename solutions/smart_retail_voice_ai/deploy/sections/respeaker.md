## Configure reSpeaker XVF3800

The reSpeaker XVF3800 microphone array requires one-time configuration before use.

### Connect to Computer

Connect the reSpeaker XVF3800 to **your computer** (not the reRouter) via USB for configuration.

### Clone Configuration Repository

```bash
git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git
```

### Navigate to Control Folder

Choose the folder matching your operating system:

| OS | Folder Path |
|----|-------------|
| Linux x86_64 | `host_control/linux_x86_64` |
| Raspberry Pi 64-bit | `host_control/rpi_64bit` |
| macOS ARM64 (Apple Silicon) | `host_control/mac_arm64` |
| NVIDIA Jetson | `host_control/jetson` |

```bash
cd reSpeaker_XVF3800_USB_4MIC_ARRAY/host_control/<YOUR_HOST_DIR>
```

### Run Configuration Commands

Grant execution permission and run the configuration sequence:

```bash
chmod +x ./xvf_host

# 1. Clear existing configuration
sudo ./xvf_host clear_configuration 1

# 2. Enable specific audio manager setting
sudo ./xvf_host audio_mgr_op_r 8 0

# 3. Save configuration
sudo ./xvf_host save_configuration 1
```

### Connect to reRouter

After configuration, disconnect the reSpeaker from your computer and connect it to the **reRouter's USB port**.
