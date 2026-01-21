## Overview

Indoor positioning is a common challenge across many industries. While high-precision systems like UWB exist, they can be costly and complex. This solution offers a flexible and cost-effective alternative by combining two powerful wireless technologies: **Bluetooth Low Energy (BLE)** for location sensing and **LoRaWAN** for long-range, low-power data transmission.

Built around the SenseCAP T1000 Tracker, this system supports two distinct positioning modes:

| Mode | Description | Best For |
|------|-------------|----------|
| **Triangulation** | Calculate precise (x, y) coordinates when 3+ beacons detected | Asset/personnel movement tracking |
| **Proximity** | Identify location based on nearest beacon | Check-ins, presence detection |

## Key Features

- **Cost-Effective & Scalable** - Uses affordable BLE beacons without expensive gateway installations in every room
- **Long-Range Transmission** - Single LoRaWAN gateway covers entire buildings or campuses
- **Instant SOS Alerts** - Emergency button triggers immediate alerts with last known location
- **Smart Power Management** - Motion-activated reporting extends battery life up to 6 months
- **Simple Deployment** - Quick setup of BLE beacons and LoRaWAN gateway
- **Open Source** - Fully customizable backend with published GitHub repository

## Use Cases

### Campus & School Safety
Provide wearable trackers to students and staff. The built-in SOS button allows instant emergency alerts from anywhere on campus.

### Asset Management
Track valuable assets indoors and outdoors. Configure trackers to report only when movement is detected, saving battery while ensuring alerts for unauthorized movement.

### Automatic Check-In & Attendance
Create "check-in" zones for offices or care facilities by adjusting BLE beacon signal strength. Presence is automatically recorded when a person with a tracker enters the zone.

## System Architecture

The system operates on a simple yet powerful principle:

1. **BLE Beacons** - Fixed transmitters placed at known locations, continuously broadcasting unique IDs
2. **SenseCAP T1000 Tracker** - Mobile device that scans for nearby beacons and identifies the strongest signal
3. **LoRaWAN Gateway** - Receives tracker data packets containing nearest beacon IDs
4. **Application Server** - Maps beacon IDs to physical locations and visualizes tracker positions
