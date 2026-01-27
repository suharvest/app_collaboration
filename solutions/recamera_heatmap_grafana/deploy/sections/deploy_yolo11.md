YOLO11 uses DFL (Distribution Focal Loss) for more accurate bounding box regression, achieving **~8 FPS** on reCamera.

### Note

After deployment, use MQTT topic `recamera/yolo11/detections` in the preview step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check IP address and network connectivity |
| Authentication failed | Try password `recamera` or `recamera.2` |
| Package install failed | Reboot device and retry |
| Conflict with YOLO26 | YOLO11 deployment will automatically stop YOLO26 service |
