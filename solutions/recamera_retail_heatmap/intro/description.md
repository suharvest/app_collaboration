## Solution Overview

This solution deploys a real-time people flow detection and heatmap visualization system on reCamera devices. Using the YOLO26 model, it can detect and track people in retail environments, analyze their behavior patterns, and generate dynamic heatmaps showing high-traffic areas.

## Key Features

- **Real-time Detection** - YOLO26 model runs directly on reCamera edge device
- **Behavior Analysis** - Automatically classifies person states (browsing, engaged, need assistance)
- **Heatmap Visualization** - Dynamic heatmap shows where people spend the most time
- **Privacy-first** - All processing happens on-device, no video leaves the store
- **Easy Integration** - MQTT output for integration with other systems

## Use Cases

| Scenario | Description |
|----------|-------------|
| Store Layout Optimization | Identify high-traffic zones and dead spots to optimize product placement |
| Customer Service | Alert staff when customers may need assistance (long dwell time) |
| Conversion Analysis | Track browsing vs. engaged behavior patterns |
| Queue Management | Monitor checkout areas and wait times |

## Technical Specifications

| Component | Specification |
|-----------|--------------|
| Detection Model | YOLO26n (INT8 quantized) |
| Inference Speed | ~300ms per frame |
| Output Format | MQTT JSON messages |
| Video Stream | RTSP (port 8554) |
| Tracking | Multi-object tracking with state analysis |

## Person States

The system classifies each detected person into one of four states:

- **Transient** - Moving through the area (speed > 10 px/s)
- **Dwelling** - Brief stop (< 1.5 seconds)
- **Engaged** - Actively browsing/interested (1.5s - 20s dwell)
- **Assistance** - May need help (> 20 seconds dwell)
