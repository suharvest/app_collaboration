## Prerequisites

Before starting the preview, ensure you have:

1. **RTSP Stream Source**: A camera or video source that provides an RTSP stream
2. **MQTT Broker**: A running MQTT broker (e.g., Mosquitto) that publishes inference results
3. **FFmpeg**: Installed on the server for RTSP to HLS conversion

## Quick Test

For testing without real hardware, you can use:

- **RTSP**: `rtsp://rtsp.stream/demo` (public test stream)
- **MQTT**: Set up a local Mosquitto broker and publish test messages

## Expected MQTT Message Format

The preview expects JSON messages with inference results. Example:

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
