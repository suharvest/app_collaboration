### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB-C 连接**电脑** | 配置阶段必须连电脑，不要连 reRouter |
| 电脑 | 需要终端/命令行 | Windows 用 PowerShell，Mac/Linux 用终端 |

### 为什么要配置

reSpeaker 出厂默认启用了回声消除功能，会影响本方案的录音效果。需要关闭这个功能。

### 配置步骤

1. 用 USB-C 线将 reSpeaker 连接到**电脑**（注意：不是 reRouter）
2. 确认电脑识别到设备（Windows 设备管理器 / Mac 系统信息）
3. 下载配置工具：
   ```bash
   git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git
   cd reSpeaker_XVF3800_USB_4MIC_ARRAY
   ```
4. 进入对应系统目录（`windows` / `macos` / `linux`）
5. 执行配置命令：
   ```bash
   # Mac/Linux 需要加 sudo
   sudo ./xvf_host clear_configuration 1
   sudo ./xvf_host audio_mgr_op_r 8 0
   sudo ./xvf_host save_configuration 1
   ```
6. 配置完成后，**断开电脑**，将 reSpeaker 连接到 **reRouter 的 USB 口**

