## 部署 YOLO26 检测器

此步骤将在您的 reCamera 设备上安装人员检测服务。

### 连接信息

输入 reCamera 的 IP 地址和 SSH 密码。默认凭证：
- **用户名**: `recamera`
- **密码**: `recamera` 或 `recamera.2`

### 部署步骤

部署过程将自动完成：

1. **连接** - 建立与 reCamera 的 SSH 连接
2. **停止冲突服务** - 停止 Node-RED 和其他冲突服务
3. **传输文件** - 上传 .deb 软件包和模型文件
4. **安装** - 通过 `opkg install --force-reinstall` 安装软件包
5. **部署模型** - 复制模型到 `/userdata/local/models/`
6. **配置 MQTT** - 启用 1883 端口的外部 MQTT 访问
7. **禁用冲突服务** - 防止冲突服务自动启动
8. **启动服务** - 启动 YOLO26 检测器服务
9. **验证** - 确认服务正在运行

### 部署完成后

部署完成后，服务将：
- 设备启动时自动运行
- 通过 RTSP 在 `rtsp://<设备IP>:8554/live0` 输出视频流
- 向 MQTT 主题 `recamera/yolo26/detections` 发布检测结果

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 检查 IP 地址和网络连接 |
| 认证失败 | 尝试密码 `recamera` 或 `recamera.2` |
| 软件包安装失败 | 设备可能需要重启后重试 |
| 服务无法启动 | 使用 `journalctl -u yolo26-detector` 查看日志 |
