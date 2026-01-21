## Deployment Overview

This solution deploys a complete edge-based voice AI system for retail environments. The deployment consists of three main steps:

1. **Flash OpenWrt Firmware** - Install the optimized OpenWrt firmware on your reRouter
2. **Configure reSpeaker** - Set up the XVF3800 microphone array on your computer
3. **Deploy Voice Services** - Automatically deploy Docker containers to reRouter

## Prerequisites

Before starting, ensure you have:

- reRouter CM4 with at least 4GB RAM and 32GB storage
- reSpeaker XVF3800 4-mic array
- USB-C cable for reSpeaker configuration
- Network cable for reRouter connection
- Computer running Linux, macOS, or Windows (for reSpeaker setup)

## Network Configuration

After deployment, access the following interfaces:

| Interface | URL | Description |
|-----------|-----|-------------|
| OpenWrt Admin | http://192.168.49.1 | Router configuration |
| Voice Client | http://192.168.49.1:8090 | Real-time ASR and device settings |
