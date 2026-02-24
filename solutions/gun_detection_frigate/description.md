## What This Solution Does

Security cameras are everywhere, but someone still has to watch them 24/7 to spot a threat. This solution adds AI-powered gun detection to your existing cameras — the system watches every frame and alerts you the moment a gun appears.

## Core Value

| Benefit | Details |
|---------|---------|
| Instant detection | AI scans every video frame in real-time, no human fatigue |
| Works offline | Runs entirely on local hardware, no cloud dependency, no data leaves your network |
| Easy to set up | One-click deployment, starts with demo videos so you can see it working immediately |
| Hardware flexible | Choose NVIDIA Jetson (GPU) or reComputer R2000 + Hailo (NPU) based on your needs |

## Use Cases

| Scenario | How It Works |
|----------|-------------|
| School safety | Install IP cameras at entrances, get instant alerts when a gun is detected |
| Retail security | Monitor store cameras 24/7, automatically flag gun-related events with recordings |
| Office building | Add gun detection to existing CCTV system, integrate alerts via MQTT |
| Public venues | Real-time monitoring across multiple cameras with centralized web dashboard |

## Prerequisites

### Hardware Requirements

| Device | Purpose | Required |
|--------|---------|----------|
| NVIDIA Jetson or reComputer R2000 + Hailo | Edge AI computing | One required |
| IP Camera (RTSP) or USB Camera | Video source | Optional (demo videos included) |

### Network Requirements

- Target device and your computer must be on the same network
- For IP cameras: cameras must be accessible via RTSP from the target device
