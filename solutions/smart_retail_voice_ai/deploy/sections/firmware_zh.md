### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reRouter CM4 | 取出 SD 卡或 eMMC 模块 | 用于刷写固件 |
| SD 卡/eMMC | 插入读卡器连接电脑 | 建议使用 USB 3.0 读卡器 |

### 刷写步骤

1. 下载固件：[全球版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-global.img.gz) | [中国版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/openwrt-bcm27xx-bcm2711-rpi-4-ext4-factory-cn.img.gz)
2. 下载 [Raspberry Pi Imager](https://www.raspberrypi.com/software/) 刷机工具
3. 选择"自定义镜像"，选择下载的固件文件
4. 选择目标存储设备（SD 卡或 eMMC）
5. 点击"写入"，等待完成
6. 将存储设备装回 reRouter，接线上电

### 首次连接

1. 用网线将电脑连接到 reRouter 的 **LAN 口**
2. 用另一根网线将 **WAN 口** 连接到路由器
3. 等待 1-2 分钟启动完成
4. 浏览器访问 `http://192.168.49.1`
5. 登录：用户名 `root`，密码留空

