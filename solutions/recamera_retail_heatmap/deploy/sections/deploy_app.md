## Deploy YOLO26 Detector

This step installs the people detection service on your reCamera device.

### Connection

Enter your reCamera's IP address and SSH password. The default credentials are:
- **Username**: `recamera`
- **Password**: `recamera` or `recamera.2`

### Deployment Steps

The deployment process will automatically:

1. **Connect** - Establish SSH connection to reCamera
2. **Stop Conflicts** - Stop Node-RED and other conflicting services
3. **Transfer** - Upload .deb package and model file
4. **Install** - Install package via `opkg install --force-reinstall`
5. **Deploy Model** - Copy model to `/userdata/local/models/`
6. **Configure MQTT** - Enable external MQTT access on port 1883
7. **Disable Conflicts** - Prevent conflicting services from auto-starting
8. **Start Service** - Start the YOLO26 detector service
9. **Verify** - Confirm service is running

### After Deployment

Once deployed, the service will:
- Automatically start on device boot
- Stream video via RTSP at `rtsp://<device_ip>:8554/live0`
- Publish detection results to MQTT topic `recamera/yolo26/detections`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check IP address and network connectivity |
| Authentication failed | Try password `recamera` or `recamera.2` |
| Package install failed | Device may need a reboot, then retry |
| Service won't start | Check logs with `journalctl -u yolo26-detector` |
