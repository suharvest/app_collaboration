## Hardware Required

- **SenseCAP T1000 Tracker** - At least one unit for testing
- **BC01 BLE Beacons** - 3+ beacons for triangulation, or 1+ for proximity mode
- **SenseCAP M2 Gateway** - Or any compatible LoRaWAN gateway
- **A computer** with Docker installed for running the positioning server

## Preset: Starter Kit {#starter}

Best for small offices or single rooms up to 500 sqm. Quick to set up, minimal hardware required.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC01 BLE Beacons | 6 | Position reference points |
| SenseCAP T1000 Tracker | 1+ | Tracked asset/person |

**What you'll get:**
- Real-time location of tracked assets/people
- Web-based map visualization
- Zone-based or triangulation positioning

**Coverage:** Up to 500 sqm · 2km LoRaWAN range

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

### Install Beacons

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Beacon light not on | Battery depleted | Replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large | Increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed | Adjust installation position |

---

## Step 2: Setup LoRaWAN Gateway {#gateway type=manual required=true}

### Gateway Setup

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| LED not on | Power issue | Check power adapter and cable |
| LED blinking red | Network not connected | Check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet | Ensure gateway is connected to the internet |
| Tracker data not reporting | Frequency band mismatch | Confirm gateway and tracker use the same frequency band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_local.yaml}

### Target: Local Deployment {#app_server_local config=devices/app_local.yaml default=true}

## Local Deployment

Deploy the indoor positioning application on your local computer.

### Requirements

- Docker Desktop installed and running
- Port 5173 available

### After Deployment

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Deployment failed | Docker not running | Start Docker Desktop |
| Port occupied | Other program using port 5173 | Close the program or change port |
| Webpage won't open | Service not fully started | Wait a few minutes and refresh the page |

### Target: Remote Deployment {#app_server_remote config=devices/app_remote.yaml}

## Remote Deployment

Deploy the indoor positioning application to a remote server via SSH.

### Before You Begin

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### After Deployment

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| SSH connection failed | IP or credentials incorrect | Check IP address and username/password |
| Deployment failed | Remote server has no Docker | Install Docker on the remote server |
| Webpage won't open | Firewall blocking | Open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

### Configure Tracker

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Keeps blinking after power on | Failed to join network | Check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured | Check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode | Press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured | Check if beacon position markers on webpage are correct |

---

## Preset: Standard Setup {#standard}

Best for medium facilities (500-2000 sqm) like warehouses, offices, or retail stores.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC01 BLE Beacons | 15 | Position reference points |
| SenseCAP T1000 Tracker | 3+ | Tracked assets/people |

**What you'll get:**
- Real-time location of tracked assets/people
- Multi-zone coverage with meter-level accuracy
- Web-based map visualization with history

**Coverage:** Up to 2000 sqm · Multiple rooms/floors supported

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

### Install Beacons

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Beacon light not on | Battery depleted | Replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large | Increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed | Adjust installation position |

---

## Step 2: Setup LoRaWAN Gateway {#gateway type=manual required=true}

### Gateway Setup

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| LED not on | Power issue | Check power adapter and cable |
| LED blinking red | Network not connected | Check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet | Ensure gateway is connected to the internet |
| Tracker data not reporting | Frequency band mismatch | Confirm gateway and tracker use the same frequency band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_local.yaml}

### Target: Local Deployment {#app_server_local config=devices/app_local.yaml default=true}

## Local Deployment

Deploy the indoor positioning application on your local computer.

### Requirements

- Docker Desktop installed and running
- Port 5173 available

### After Deployment

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Deployment failed | Docker not running | Start Docker Desktop |
| Port occupied | Other program using port 5173 | Close the program or change port |
| Webpage won't open | Service not fully started | Wait a few minutes and refresh the page |

### Target: Remote Deployment {#app_server_remote config=devices/app_remote.yaml}

## Remote Deployment

Deploy the indoor positioning application to a remote server via SSH.

### Before You Begin

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### After Deployment

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| SSH connection failed | IP or credentials incorrect | Check IP address and username/password |
| Deployment failed | Remote server has no Docker | Install Docker on the remote server |
| Webpage won't open | Firewall blocking | Open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

### Configure Tracker

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Keeps blinking after power on | Failed to join network | Check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured | Check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode | Press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured | Check if beacon position markers on webpage are correct |

---

## Preset: Enterprise {#enterprise}

Best for large facilities (2000+ sqm) like factories, hospitals, or campus buildings.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1+ | LoRaWAN coverage (add more for larger areas) |
| BC01 BLE Beacons | 30+ | Position reference points |
| SenseCAP T1000 Tracker | 10+ | Tracked assets/people |

**What you'll get:**
- Campus-wide real-time tracking
- High-precision triangulation positioning
- Scalable to thousands of tracked assets

**Coverage:** 2000+ sqm · Add gateways for multi-building coverage

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

### Install Beacons

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Beacon light not on | Battery depleted | Replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large | Increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed | Adjust installation position |

---

## Step 2: Setup LoRaWAN Gateway {#gateway type=manual required=true}

### Gateway Setup

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| LED not on | Power issue | Check power adapter and cable |
| LED blinking red | Network not connected | Check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet | Ensure gateway is connected to the internet |
| Tracker data not reporting | Frequency band mismatch | Confirm gateway and tracker use the same frequency band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_local.yaml}

### Target: Local Deployment {#app_server_local config=devices/app_local.yaml default=true}

## Local Deployment

Deploy the indoor positioning application on your local computer.

### Requirements

- Docker Desktop installed and running
- Port 5173 available

### After Deployment

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Deployment failed | Docker not running | Start Docker Desktop |
| Port occupied | Other program using port 5173 | Close the program or change port |
| Webpage won't open | Service not fully started | Wait a few minutes and refresh the page |

### Target: Remote Deployment {#app_server_remote config=devices/app_remote.yaml}

## Remote Deployment

Deploy the indoor positioning application to a remote server via SSH.

### Before You Begin

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### After Deployment

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| SSH connection failed | IP or credentials incorrect | Check IP address and username/password |
| Deployment failed | Remote server has no Docker | Install Docker on the remote server |
| Webpage won't open | Firewall blocking | Open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

### Configure Tracker

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| Keeps blinking after power on | Failed to join network | Check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured | Check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode | Press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured | Check if beacon position markers on webpage are correct |

---

# Deployment Complete

## Deployment Successful!

The Indoor Positioning Application is now running.

### Access Your Dashboard

Open your browser and navigate to: **http://localhost:5173**

### Default Login Credentials

- **Username:** admin
- **Password:** 83EtWJUbGrPnQjdCqyKq

> **Important:** Change the default password after your first login for security.

### Next Steps

1. Upload your floor map image in the Map settings
2. Add beacon positions by clicking on the map
3. Configure your LoRaWAN network server connection
4. Activate your T1000 tracker and start tracking!

### Need Help?

- [Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
