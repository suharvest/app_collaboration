This solution deploys a real-time traffic heatmap system with four components:

1. **Database** - Stores location data detected by reCamera
2. **reCamera** - Runs person detection on the camera, auto-blurs people and only transmits coordinates
3. **Dashboard** - Displays traffic statistics and trends with charts
4. **Heatmap** - Shows crowd gathering areas visually on your floor plan

## Network Requirements

Ensure reCamera and your computer are on the **same WiFi network**. This allows:
- reCamera to send data to your computer
- Dashboard to display live feed from reCamera
- Heatmap to query location data from the database

## Preset: Simple Preview {#simple}

Deploy heatmap application to reCamera for real-time person detection and heat visualization. No backend server required.

## Connection Options

| Method | IP Address | Notes |
|--------|------------|-------|
| USB Connection | 192.168.42.1 | Direct USB-C connection |
| Wired Network | Check router | Most reliable |
| WiFi | Check router | May need initial USB setup |

## Default Credentials

- **Username**: `recamera`
- **Password**: `recamera` or `recamera.2`

## Step 1: Deploy Detector {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

### Target: YOLO11 (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

YOLO11 uses DFL (Distribution Focal Loss) for more accurate bounding box regression, achieving **~8 FPS** on reCamera.

### Note

After deployment, use MQTT topic `recamera/yolo11/detections` in the preview step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check IP address and network connectivity |
| Authentication failed | Try password `recamera` or `recamera.2` |
| Package install failed | Reboot device and retry |
| Conflict with YOLO26 | YOLO11 deployment will automatically stop YOLO26 service |

### Target: YOLO26 (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

### Troubleshooting

The service will automatically start on device boot. You can verify it's working by checking the preview in the next step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Check IP address and network connectivity |
| Authentication failed | Try password `recamera` or `recamera.2` |
| Package install failed | Reboot device and retry |

---

## Step 2: Live Preview with Heatmap {#preview type=preview required=false config=devices/preview.yaml}

Click **Connect** to view the live video with heatmap overlay.

**Tips:** The heatmap accumulates over time - give it a few minutes to build up.

---

## Preset: Grafana Dashboard {#grafana}

This solution deploys a real-time traffic heatmap system with four components:

1. **Database** - Stores location data detected by reCamera
2. **reCamera** - Runs person detection on the camera, auto-blurs people and only transmits coordinates
3. **Dashboard** - Displays traffic statistics and trends with charts
4. **Heatmap** - Shows crowd gathering areas visually on your floor plan

## Network Requirements

Ensure reCamera and your computer are on the **same WiFi network**. This allows:
- reCamera to send data to your computer
- Dashboard to display live feed from reCamera
- Heatmap to query location data from the database

## Step 1: Deploy InfluxDB + Grafana {#backend type=docker_deploy required=true config=devices/backend.yaml}

### Target: Local Deployment {#backend_local config=devices/backend.yaml default=true}

## Local Deployment

Deploy the database and dashboard services on your computer.

### Prerequisites

- Docker Desktop installed and running
- At least 2GB free disk space
- Ports 8086 and 3000 available

![Wiring](intro/gallery/architecture.svg)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

#### Troubleshooting

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Deployment fails with port conflict | Port 8086 or 3000 in use | Close the program using the port, or change the port in configuration |
| Docker won't start | Docker Desktop not running | Open the Docker Desktop application |
| Container stops after starting | Insufficient memory | Ensure at least 4GB RAM available |

### Target: Remote Deployment {#backend_remote config=devices/backend_remote.yaml}

# Remote Deployment

Deploy InfluxDB and Grafana to a remote device (reComputer, Raspberry Pi, etc.).

## Before You Begin

1. **Connect target device to the network**
   - Ensure the device is on the same network as your computer
   - Note down the device's IP address

2. **Get device credentials**
   - SSH username (usually `root`, `pi`, or `recomputer`)
   - SSH password

## Connection Settings

Enter the following information:

| Field | Description | Example |
|-------|-------------|---------|
| Device IP | Target device IP address | 192.168.1.100 |
| SSH Username | Login username | root |
| SSH Password | Login password | your-password |
| SSH Port | SSH port (default 22) | 22 |

## After Deployment

Access InfluxDB: `http://<device-ip>:8086`
- Credentials: admin / adminpassword
- Organization: seeed, Bucket: recamera

Go to **API Tokens** and copy the token for later configuration.

Access Grafana: `http://<device-ip>:3000`
- Default credentials: admin / admin

![Wiring](intro/gallery/architecture.svg)

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

---

## Step 2: Configure reCamera {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

## Configure reCamera

Set up reCamera to send detected traffic data to the database.

### Steps

1. Visit [SenseCraft reCamera](https://sensecraft.seeed.cc/ai/recamera) and deploy the heatmap app to your reCamera
2. Open reCamera's Node-RED interface and install the `node-red-contrib-influxdb` node
3. Configure the database node:
   - URL: `http://<your-computer-ip>:8086`
   - Paste the API token from the previous step
4. Click Deploy to activate the flow

### Troubleshooting

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Node installation fails | Network issue | Check if reCamera can access the internet |
| Database connection fails | Wrong IP address | Verify your computer's IP; ensure reCamera and computer are on the same network |
| No data in database | Invalid token | Get a new API token from the database |

---

## Step 3: Configure Grafana Dashboard {#grafana_config type=manual required=true}

## Configure Dashboard

Connect the database to Grafana and import the pre-built chart templates.

### Steps

1. Open your browser and go to `http://localhost:3000`
2. Log in with default credentials: admin / admin
3. Add data source:
   - Go to **Connections** > **Data sources** > click **Add data source**
   - Select **InfluxDB**
   - Set Query Language to **Flux**
   - URL: `http://influxdb:8086`
   - Paste your API token
   - Click **Save & Test**
4. Import chart templates:
   - Go to **Dashboards** > **Import**
   - Upload the dashboard JSON file provided with this solution

### Troubleshooting

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Cannot access localhost:3000 | Service not running | Go back and check deployment status |
| Data source test fails | Incorrect token | Copy the complete API token again from the database |
| Charts show no data | reCamera not sending data | Check if reCamera's Node-RED is running properly |

---

## Step 4: Calibrate and Configure Heatmap {#heatmap type=manual required=true}

## Configure Heatmap

Calibrate the camera view to match your floor plan, so traffic data displays correctly on the map.

### Steps

1. **Prepare Materials**
   - Export a screenshot from your reCamera
   - Prepare your store/venue floor plan image

2. **Calibrate Reference Points**
   - Run the calibration tool: `python calibration_tool.py`
   - Click 4 corner reference points on the camera screenshot
   - Click the corresponding 4 points on the floor plan
   - The tool will generate calibration code

3. **Configure the Page**
   - Paste the generated calibration code into `index.html`
   - Fill in database connection info (IP, Token)

4. **Start the Service**
   - Run `python -m http.server 8080`
   - Open `http://localhost:8080` in your browser to view the result

### Troubleshooting

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Traffic positions appear offset | Inaccurate calibration points | Re-run calibration tool, choose more visible reference points |
| Page shows blank | Database connection failed | Verify Token and IP address are correct |
| Data appears delayed | Network issue | Check network connection stability |

---

# Deployment Complete

## Deployment Complete!

Your real-time heatmap system is now running.

### Access Points

| Service | URL |
|---------|-----|
| Grafana Dashboard | http://localhost:3000 |
| Heatmap Page | http://localhost:8080/index.html |
| InfluxDB UI | http://localhost:8086 |

### Grafana Login

- Username: `admin`
- Password: `admin` (change on first login)

### What's Next?

1. **Calibrate the Heatmap** - Run the Python calibration tool to map camera coordinates to your floor plan
2. **Customize the Dashboard** - Add or modify Grafana panels to suit your needs
3. **Adjust Heatmap Settings** - Configure refresh interval and accumulation mode in index.html

### Troubleshooting

- **No data in Grafana**: Check that reCamera is connected and Node-RED flow is deployed
- **Heatmap not loading**: Verify InfluxDB credentials in index.html
- **Video feed disconnected**: This is normal due to reCamera resource limits; it will reconnect automatically
