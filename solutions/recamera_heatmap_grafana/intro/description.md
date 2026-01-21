## Core Value

- **Edge AI Processing** - All person detection runs locally on reCamera using YOLO11n model, no cloud required
- **Privacy Protection** - Automatic blur processing on detected persons before data transmission
- **Real-time Analytics** - Live heatmap visualization showing foot traffic patterns
- **Enterprise Dashboard** - Professional data visualization with Grafana and InfluxDB time-series database

## Technical Highlights

| Feature | Description |
|---------|-------------|
| Detection Model | YOLO11n optimized for edge computing |
| Data Flow | Node-RED workflow engine on reCamera |
| Time-series DB | InfluxDB 2.x for high-performance data storage |
| Visualization | Grafana dashboards with real-time updates |
| Heatmap | HTML5 Canvas-based heat visualization |

## Application Scenarios

| Scenario | Use Case |
|----------|----------|
| Retail Analytics | Track customer foot traffic patterns and hot spots |
| Office Space | Monitor workspace utilization and optimize layout |
| Exhibition Halls | Identify popular exhibits and visitor flow |
| Public Venues | Crowd density monitoring and safety management |

## System Architecture

The solution consists of three main components:

1. **reCamera** - Edge AI device running person detection and privacy blur
2. **InfluxDB** - Time-series database storing detection coordinates
3. **Grafana** - Dashboard displaying real-time heatmap and statistics

Data flows from reCamera through Node-RED to InfluxDB, with Grafana querying the database for visualization.
