## 刷写 OpenWrt 固件

reRouter 需要刷入定制的 OpenWrt 固件，该固件包含 Docker 支持和音频驱动。

### 下载固件

根据您的地区选择固件版本：

| 地区 | 下载链接 |
|------|---------|
| 全球版 | [openwrt-global.img.gz](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-global.img.gz) |
| 中国大陆版 | [openwrt-cn.img.gz](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-cn.img.gz) |

### 刷写步骤

1. 下载并安装 [Raspberry Pi Imager](https://www.raspberrypi.com/software/) 或 [balenaEtcher](https://etcher.balena.io/)
2. 解压下载的固件（.img.gz）
3. 将固件刷入 reRouter 的 SD 卡或 eMMC
4. 详细说明请参考 [reRouter 刷机指南](https://wiki.seeedstudio.com/cn/OpenWrt-Getting-Started/#初始设置)

> **重要提示**：请使用上方提供的固件，而非通用 OpenWrt 指南页面中的固件。

### 硬件连接

刷写完成后，连接 reRouter：

- **WAN 口**：连接到路由器/调制解调器以访问互联网
- **LAN 口**：连接到电脑进行配置

### 验证连接

1. 连接到 Wi-Fi 热点 `OpenWrt-XXXX` 或通过网线连接
2. 打开浏览器访问 http://192.168.49.1
3. 使用用户名 `root` 登录（默认密码为空）

### 安装 Docker（如需要）

提供的固件应已预装 Docker。如果没有，请运行：

```bash
opkg update
opkg install dockerd docker containerd runc wget-ssl unzip ca-certificates
/etc/init.d/dockerd enable
/etc/init.d/dockerd start
```
