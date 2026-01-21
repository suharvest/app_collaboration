## Configure and Start Preview

1. Enter the **RTSP URL** of your video stream
2. Enter the **MQTT Broker** address where inference results are published
3. Enter the **MQTT Topic** to subscribe for inference results
4. Click **Start Preview** to connect

The video will start playing and inference results will be drawn on top of the video in real-time.

## Troubleshooting

- **Video not playing**: Check that the RTSP URL is correct and FFmpeg is installed
- **No overlay**: Verify MQTT broker is reachable and messages are being published
- **Connection timeout**: Check network connectivity and firewall settings
