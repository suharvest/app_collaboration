## Before You Begin

Ensure your system meets the following requirements:

- **Docker** installed and running (version 20.0+)
- **Network connectivity** to pull container images
- **Available ports**: 8280 (Web UI), 4841 (OPC-UA Simulator)

## Deployment Options

Choose one of the following deployment options:

### Local Deployment
Deploy directly on this machine. Best for development, testing, or when running on an edge device.

### Remote Deployment
Deploy to a remote device (e.g., reComputer R series) via SSH. Best for production deployments on dedicated hardware.

## After Deployment

Once deployed, access the web interface at:
- **Local**: http://localhost:8280
- **Remote**: http://<device-ip>:8280

### Quick Start Guide

1. **Connect to OPC-UA Server** - Enter your OPC-UA server address or use the built-in simulator
2. **Upload Training Data** - Upload historical HVAC data in CSV format
3. **Train Model** - Click "Train Model" to build the prediction model
4. **Configure Parameters** - Set up input/output parameter mappings
5. **Start Predictions** - Begin automatic parameter reading and prediction
