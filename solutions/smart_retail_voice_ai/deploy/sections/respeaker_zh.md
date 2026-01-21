## 配置 reSpeaker XVF3800

reSpeaker XVF3800 麦克风阵列在使用前需要进行一次性配置。

### 连接到电脑

使用 USB 将 reSpeaker XVF3800 连接到**您的电脑**（不是 reRouter）进行配置。

### 克隆配置仓库

```bash
git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git
```

### 进入控制目录

选择与您操作系统匹配的文件夹：

| 操作系统 | 文件夹路径 |
|---------|-----------|
| Linux x86_64 | `host_control/linux_x86_64` |
| Raspberry Pi 64 位 | `host_control/rpi_64bit` |
| macOS ARM64 (Apple Silicon) | `host_control/mac_arm64` |
| NVIDIA Jetson | `host_control/jetson` |

```bash
cd reSpeaker_XVF3800_USB_4MIC_ARRAY/host_control/<YOUR_HOST_DIR>
```

### 运行配置命令

授予执行权限并运行配置序列：

```bash
chmod +x ./xvf_host

# 1. 清除现有配置
sudo ./xvf_host clear_configuration 1

# 2. 启用特定音频管理器设置
sudo ./xvf_host audio_mgr_op_r 8 0

# 3. 保存配置
sudo ./xvf_host save_configuration 1
```

### 连接到 reRouter

配置完成后，断开 reSpeaker 与电脑的连接，将其连接到 **reRouter 的 USB 口**。
