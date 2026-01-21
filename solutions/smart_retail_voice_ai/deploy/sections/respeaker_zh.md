### 配置麦克风阵列

1. 将 reSpeaker XVF3800 用 USB 连接到**电脑**（非 reRouter）
2. 克隆配置仓库：`git clone https://github.com/respeaker/reSpeaker_XVF3800_USB_4MIC_ARRAY.git`
3. 进入对应系统目录，执行：
   ```bash
   sudo ./xvf_host clear_configuration 1
   sudo ./xvf_host audio_mgr_op_r 8 0
   sudo ./xvf_host save_configuration 1
   ```
4. 断开电脑，将 reSpeaker 连接到 **reRouter USB 口**
