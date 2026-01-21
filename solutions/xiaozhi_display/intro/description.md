## Overview

Xiaozhi Display Cast extends your SenseCAP Watcher AI assistant to large screens, perfect for:

- **Outdoor Advertising** - Digital signage with AI-powered interactive content
- **Retail Displays** - Product showcases with voice assistant capabilities
- **Conference Rooms** - Shared AI assistant on meeting room screens
- **Smart Home Hubs** - Central display for home automation

## How It Works

The system uses **UI State Sync + Web Rendering** architecture:

1. **Watcher Device** sends UI state (emotions, text, chat messages) as JSON
2. **Display Server** receives state via WebSocket and broadcasts to browsers
3. **Web Browser** renders the UI with smooth animations
4. **Audio Output** is decoded (Opus → PCM) and played through HDMI/speakers

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Client Support** | Multiple browsers can view simultaneously |
| **mDNS Discovery** | Watcher auto-discovers display server on network |
| **Customizable Theme** | Support for custom backgrounds and emoji assets |
| **Audio Amplification** | Route audio through HDMI to external speakers |
| **Low Latency** | Real-time UI synchronization via WebSocket |

## System Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│ SenseCAP Watcher│ ─────────────────► │  Display Server  │
│   (ESP32-S3)    │    UI State JSON   │  (Docker/Python) │
└─────────────────┘                    └────────┬─────────┘
                                                │
                                                │ HTTP + WebSocket
                                                ▼
                                       ┌──────────────────┐
                                       │    Web Browser   │
                                       │  (Large Screen)  │
                                       └────────┬─────────┘
                                                │
                                                │ HDMI
                                                ▼
                                       ┌──────────────────┐
                                       │ TV / Display /   │
                                       │ Advertising Screen│
                                       └──────────────────┘
```

## Requirements

- SenseCAP Watcher with custom firmware (included)
- reComputer R Series or Raspberry Pi 4/5
- HDMI display (TV, monitor, or advertising screen)
- Network connectivity (WiFi or Ethernet)
