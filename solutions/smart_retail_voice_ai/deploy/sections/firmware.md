## Flash OpenWrt Firmware

The reRouter requires a customized OpenWrt firmware that includes Docker support and audio drivers.

### Download Firmware

Choose the firmware version for your region:

| Region | Download Link |
|--------|--------------|
| Global | [openwrt-global.img.gz](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-global.img.gz) |
| China Mainland | [openwrt-cn.img.gz](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-cn.img.gz) |

### Flash Instructions

1. Download and install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or [balenaEtcher](https://etcher.balena.io/)
2. Extract the downloaded firmware (.img.gz)
3. Flash the firmware to the reRouter's SD card or eMMC
4. For detailed instructions, refer to [reRouter Flashing Guide](https://wiki.seeedstudio.com/cn/OpenWrt-Getting-Started/#初始设置)

> **Important**: Use the firmware provided above, not the one from the general OpenWrt guide page.

### Hardware Connection

After flashing, connect the reRouter:

- **WAN Port**: Connect to your router/modem for internet access
- **LAN Port**: Connect to your computer for configuration

### Verify Connection

1. Connect to Wi-Fi hotspot `OpenWrt-XXXX` or via LAN cable
2. Open browser and navigate to http://192.168.49.1
3. Login with username `root` (password is empty by default)

### Install Docker (if needed)

The provided firmware should have Docker pre-installed. If not, run:

```bash
opkg update
opkg install dockerd docker containerd runc wget-ssl unzip ca-certificates
/etc/init.d/dockerd enable
/etc/init.d/dockerd start
```
