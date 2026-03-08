## Preset: OpenClaw + Optional Local AI {#openclaw_basic}

Deploy OpenClaw AI messaging gateway, with optional local AI model powered by your device's GPU.

| Device | Purpose |
|--------|---------|
| reComputer R or Jetson | Runs OpenClaw gateway and optional local AI model |

**What you'll get:**
- AI chatbot gateway supporting 20+ messaging platforms
- Optional local AI model running on device GPU — no data leaves your network
- Web management interface for configuration

**Requirements:** Docker installed · Internet access (for first-time image download)

## Step 1: Deploy OpenClaw {#deploy_openclaw type=docker_deploy required=true config=devices/local.yaml}

Deploy the OpenClaw AI gateway. If local AI model is enabled, it will be started and configured automatically.

### Target: Local Deployment {#local type=local config=devices/local.yaml default=true}

Deploy on your reComputer R series device.

### Wiring

1. Ensure Docker is installed and running
2. Optionally check **Enable Local AI Model** and select a model
3. Click **Deploy** to start services

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. Open **http://localhost:18789** in your browser
3. Enter the token to log in
4. Connect your first messaging channel (WeChat, Telegram, Discord, etc.)
5. If local AI model is enabled, it's already configured — select it when creating an agent

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 18789 already in use | Stop the service occupying port 18789, or check if OpenClaw is already running |
| Docker not found | Install Docker Desktop and ensure it is running |
| Model download slow | Large models take time; check your internet connection |
| OpenClaw container keeps restarting | Check logs: `docker logs openclaw-gateway` |

### Target: Remote Deployment (Jetson) {#jetson_remote type=remote config=devices/jetson.yaml}

Deploy to a reComputer Jetson device over SSH, with GPU-accelerated local AI model.

### Wiring

1. Connect reComputer Jetson to the same network as your deployment machine
2. Enter Jetson IP address, SSH username, and password
3. Optionally check **Enable Local AI Model** and select a model
4. Click **Deploy** to start services

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. Open **http://\<jetson-ip\>:18789** in your browser
3. Enter the token to log in
4. Connect your first messaging channel
5. If local AI model is enabled, it's already configured with GPU acceleration — select it when creating an agent

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify Jetson IP, username, password, and that SSH service is running |
| NVIDIA runtime not detected | Ensure NVIDIA container runtime is installed: `nvidia-smi` should work |
| Docker Compose unavailable | Install it: `sudo apt-get install -y docker-compose-plugin` |
| Model download slow | First download gets the full model; subsequent runs use cache |
| Not enough disk space | Need at least 20GB free; check with `df -h /` |
| Port 11434 already in use | A local AI service may already be running; the deployer will use it automatically |

# Deployment Complete

OpenClaw AI gateway is ready to use.

## Initial Setup

1. Copy the **Gateway Token** from the deployment log
2. Open the OpenClaw web UI in your browser and enter the token to log in
3. Connect your first messaging channel (WeChat, Telegram, Discord, etc.)

## Quick Verification

- Web UI loads at the gateway URL
- If local AI model is enabled: go to Settings > Models, you should see the local model provider listed
- Send a test message through your connected messaging channel

## Next Steps

- [OpenClaw Documentation](https://github.com/nicepkg/openclaw)
- Add more AI providers in Settings > Models
- Connect additional messaging platforms
