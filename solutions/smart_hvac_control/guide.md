HVAC energy optimization system using KNN prediction model with OPC-UA integration.

## Prerequisites

- **Docker** installed and running (version 20.0+)
- **Network connectivity** to pull container images
- **Available ports**: 8280 (Web UI), 4841 (OPC-UA Simulator)

## Preset: Standard Deployment {#default}

Deploy a KNN-based HVAC optimization system that learns from your historical data to suggest optimal settings.

| Device | Purpose |
|--------|---------|
| reComputer R1100 | Edge computing device with Docker support |

**What you'll get:**
- AI-powered temperature recommendations based on historical patterns
- OPC-UA integration for industrial HVAC systems
- Web dashboard for monitoring and control

**Requirements:** Docker installed · OPC-UA controller (or use built-in simulator)

## Step 1: HVAC Control System {#hvac type=docker_deploy required=true}

### Target: Local Deployment {#hvac_local type=local config=devices/local.yaml default=true}

Click the "Deploy" button below to automatically start the HVAC control service on this machine.

![Wiring](gallery/architecture.svg)

1. Ensure Docker is installed and running
2. Click deploy to start the container
3. Access the web interface at localhost:8280

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | Start Docker Desktop application |
| Port 8280 in use | Close the program using that port, or modify config to use another port |
| Container stops after starting | Run `docker logs missionpack_knn` to check error logs |
| Web page not loading | Wait 30 seconds for the service to fully start |

### Target: Remote Deployment {#hvac_remote type=remote config=devices/remote.yaml}

Click the "Deploy" button below to automatically deploy the HVAC control service to the remote device.

![Wiring](gallery/recomputer.svg)

1. Connect to remote device via SSH
2. Deploy Docker container remotely
3. Access the web interface at device IP:8280

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check IP address and credentials |
| Remote device has no Docker | Install Docker on the remote device first |
| Deployment timeout | Check remote device network, ensure it can access image registry |
| Web page not loading | Check if firewall allows port 8280 |

---

# Deployment Complete

## Deployment Successful!

Your HVAC Automation Control System is now running.

### Next Steps

1. **Access the Web Interface** - Open your browser and navigate to the application URL
2. **Connect to OPC-UA Server** - Configure your OPC-UA server connection or use the built-in simulator
3. **Upload Training Data** - Import your historical HVAC data for model training
4. **Configure Parameters** - Set up input/output parameter mappings

### Useful Commands

Check container status:
```bash
docker ps | grep missionpack_knn
```

View application logs:
```bash
docker logs missionpack_knn
```

Restart the application:
```bash
docker restart missionpack_knn
```

### Kiosk Mode (Optional)

You can configure Kiosk mode from the Devices management page to auto-start the application in fullscreen on boot.
