This solution deploys a real-time heatmap system with four main components:

1. **InfluxDB** - Time-series database for storing detection coordinates
2. **reCamera** - Edge AI device running person detection with Node-RED
3. **Grafana** - Dashboard for visualization and analytics
4. **Heatmap Page** - HTML5 canvas-based heat visualization

## Network Requirements

Ensure reCamera and your computer are on the **same network**. This is required for:
- reCamera to send data to InfluxDB
- Grafana to display live video feed from reCamera
- Heatmap page to query data from InfluxDB
