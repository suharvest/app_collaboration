## 前提条件

开始预览前，请确保您已准备：

1. **RTSP 视频源**: 提供 RTSP 流的摄像头或视频源
2. **MQTT 服务器**: 运行中的 MQTT broker（如 Mosquitto），用于发布推理结果
3. **FFmpeg**: 服务器上已安装 FFmpeg，用于 RTSP 转 HLS 转换

## 快速测试

如果没有实际硬件，可以使用：

- **RTSP**: `rtsp://rtsp.stream/demo`（公共测试流）
- **MQTT**: 设置本地 Mosquitto 服务器并发布测试消息

## MQTT 消息格式

预览功能期望接收 JSON 格式的推理结果。示例：

```json
{
  "detections": [
    {
      "bbox": [100, 100, 200, 150],
      "class": "person",
      "confidence": 0.95
    }
  ],
  "frame_width": 640,
  "frame_height": 480
}
```
