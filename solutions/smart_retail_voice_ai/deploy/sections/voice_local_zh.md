### 硬件连接

| 设备 | 连接方式 | 注意事项 |
|------|---------|---------|
| reSpeaker XVF3800 | USB 连接到电脑 | 确保已完成步骤二的配置 |
| 电脑 | 需安装 Docker Desktop | Windows/Mac 需下载安装 |

### 前提条件

- Docker Desktop 已安装并运行
- reSpeaker XVF3800 已通过 USB 连接
- 至少 2GB 可用磁盘空间
- 端口 8090 未被占用

### 验证连接

部署前，确认 reSpeaker 被识别：
- **Windows**: 设备管理器 > 声音、视频和游戏控制器
- **Mac**: 系统偏好设置 > 声音 > 输入，选择 XVF3800
- **Linux**: 执行 `arecord -l` 查看录音设备

