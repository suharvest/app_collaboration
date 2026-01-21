## Deployment Overview

This solution deploys a real-time heatmap system with four main components:

1. **InfluxDB** - Time-series database for storing detection coordinates
2. **reCamera** - Edge AI device running person detection with Node-RED
3. **Grafana** - Dashboard for visualization and analytics
4. **Heatmap Page** - HTML5 canvas-based heat visualization

## Prerequisites

- reCamera device (2002 series, Gimbal, or HQ POE)
- Computer running Windows, macOS, or Linux
- Docker installed (for local InfluxDB/Grafana deployment)
- Network connection between reCamera and computer

## Network Requirements

Ensure reCamera and your computer are on the **same network**. This is required for:
- reCamera to send data to InfluxDB
- Grafana to display live video feed from reCamera
- Heatmap page to query data from InfluxDB

## After Deployment

Once all steps are complete, you can access:
- **Grafana Dashboard**: http://localhost:3000
- **Heatmap Page**: http://localhost:8080/index.html
- **InfluxDB UI**: http://localhost:8086
