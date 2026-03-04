## Preset: Jetson One-Click Depth Demo {#jetson_depth}

Deploy Depth Anything V3 to your Jetson device with one click from this platform.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson (reComputer) | Runs Depth Anything V3 in Docker |
| USB Camera (optional) | Real-time depth inference input |

**What you'll get:**
- Automatic remote deployment through SSH
- Preconfigured Docker container with GPU runtime
- Ready-to-run Depth Anything V3 environment on Jetson

**Requirements:** Jetson on Linux + SSH reachable + Docker available

## Step 1: Deploy Depth Anything V3 {#deploy_depth_anything type=docker_deploy required=true config=devices/jetson.yaml}

Deploy the containerized runtime to your Jetson. No terminal command input is required from the user.

### Target: Remote Deployment (Jetson) {#jetson_remote type=remote config=devices/jetson.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect Jetson to the same network as your computer
2. Plug in USB camera if you want live depth inference
3. Fill in Jetson IP, SSH username, and password
4. Click **Deploy**

### Deployment Complete

1. The Docker container is running on your Jetson
2. USB camera inference starts automatically in the container
3. RTSP output is published at `rtsp://<jetson-ip>:8554/depth`
4. No additional command input is required for deployment completion

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password, and that Jetson SSH service is enabled |
| Docker runtime check failed | Ensure Docker is installed and NVIDIA runtime is available on Jetson |
| Disk space not enough | Free space on Jetson root partition and deploy again |
| Deployment timeout | Keep Jetson online and retry after checking network quality |
| RTSP stream not available | Check camera is attached under `/dev/video*` and inspect logs: `docker logs depth_anything_v3` |

## Step 2: Preview Depth Video Stream {#preview_depth_stream type=preview required=false config=devices/preview.yaml}

Use this step to view your Jetson RTSP inference stream directly in the platform UI.

### Wiring

1. Connect a USB camera to Jetson (check it appears as `/dev/video0` or another `/dev/video*`)
2. Ensure your inference pipeline publishes RTSP on Jetson (recommended path: `rtsp://<jetson-ip>:8554/depth`)
3. In this step, enter that RTSP URL
4. Click **Connect** to start preview

### Deployment Complete

1. Live stream is visible in the preview window
2. If your pipeline outputs depth/overlay frames, they are shown in real time
3. You can disconnect/reconnect without redeploying Step 1

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Preview black screen | Verify RTSP URL with VLC first, then retry in this page |
| Connection timeout | Confirm Jetson port `8554` is reachable from the machine running this platform |
| ffmpeg not found | Install ffmpeg on the machine running this platform/backend |
| Only raw camera seen | Your Jetson pipeline is likely publishing camera passthrough; switch RTSP source to your inference output stream |

# Deployment Complete

Depth Anything V3 runtime has been deployed successfully on your Jetson.

## Validation Checklist

1. Deployment status shows success in this page
2. The service container stays in running state
3. You can proceed to your next product integration step directly
