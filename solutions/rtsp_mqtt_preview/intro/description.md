## Overview

This demo showcases the **Live Preview** feature that enables real-time video streaming with inference result overlay. It combines:

- **RTSP Video Streaming**: View live camera feeds through your browser
- **MQTT Message Display**: Receive and visualize inference results in real-time
- **Canvas Overlay**: Draw bounding boxes, labels, and other annotations on the video

## Use Cases

| Scenario | Description |
|----------|-------------|
| AI Camera Monitoring | View object detection results from edge AI cameras |
| Quality Inspection | Monitor manufacturing line with defect detection overlay |
| Smart Retail | Display customer analytics and heatmaps |
| Security Systems | View person/vehicle detection in real-time |

## How It Works

1. **RTSP to HLS Conversion**: The backend converts RTSP streams to HLS format for browser playback
2. **MQTT to WebSocket Bridge**: MQTT messages are forwarded to the browser via WebSocket
3. **Canvas Rendering**: Custom or built-in renderers draw inference results on top of the video

## Supported Data Formats

The preview automatically detects and renders common inference result formats:

- **Bounding Boxes**: Object detection results with classes and confidence scores
- **Pose Keypoints**: Human pose estimation with skeleton connections
- **Segmentation Masks**: Instance or semantic segmentation results
- **Classifications**: Image classification with confidence bars
- **Heatmaps**: Attention or saliency map overlays

## Custom Rendering

Developers can provide custom drawing scripts for specialized visualizations. See the documentation for the overlay script API.
