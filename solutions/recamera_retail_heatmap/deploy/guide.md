## Deployment Overview

This deployment will install the YOLO26 people detection service on your reCamera device and enable real-time heatmap visualization.

## Prerequisites

- **reCamera device** connected to your network (wired or USB)
- **Network access** to the reCamera from your computer
- **SSH credentials** (default user: `recamera`, password: `recamera` or `recamera.2`)

## Network Connection Options

| Method | IP Address | Notes |
|--------|------------|-------|
| USB Connection | 192.168.42.1 | Direct USB-C connection |
| Wired Network | Check router | Most reliable |
| WiFi | Check router | May need initial USB setup |

## What Will Be Deployed

1. **YOLO26 Detector Package** - Debian package with detection binary and init script
2. **AI Model** - YOLO26n INT8 quantized model for person detection
3. **MQTT Configuration** - Enable external access for preview

## Automatic Configuration

The deployment will automatically:

- Stop conflicting services (Node-RED, sscma-node, supervisor)
- Install the detection software via `opkg`
- Deploy the AI model to `/userdata/local/models/`
- Configure MQTT for external access
- Disable conflicting services from auto-start
- Start the detection service
