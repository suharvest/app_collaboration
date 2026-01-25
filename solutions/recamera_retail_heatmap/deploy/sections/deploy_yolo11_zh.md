YOLO11 使用 DFL (Distribution Focal Loss) 进行更精确的边界框回归，在 reCamera 上可达 **~8 FPS**。

### 注意

部署完成后，在预览步骤中使用 MQTT 主题 `recamera/yolo11/detections`。

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 检查 IP 地址和网络连接 |
| 认证失败 | 尝试密码 `recamera` 或 `recamera.2` |
| 软件包安装失败 | 重启设备后重试 |
| 与 YOLO26 冲突 | YOLO11 部署会自动停止 YOLO26 服务 |
