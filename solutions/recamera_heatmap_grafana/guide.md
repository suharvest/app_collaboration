This solution tracks where people walk in your store and shows it as a heatmap.

**How it works:**
1. reCamera watches the area and detects people (faces are automatically blurred)
2. Location data is sent to your computer
3. You see a visual map of busy vs quiet areas

## Network Requirements

Make sure reCamera and your computer are on the **same WiFi network**.

## Preset: Quick Preview {#simple}

See heatmap directly on reCamera's web interface - no extra computer or dashboard needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera with person detection |

**What you'll get:**
- Live video with heatmap overlay
- See busy vs quiet areas in real-time
- Privacy-preserving (faces automatically blurred)

**Requirements:** reCamera and your computer on the same network

## How to Connect

| Method | IP Address | Notes |
|--------|------------|-------|
| USB Cable | 192.168.42.1 | Plug USB-C directly into computer |
| Network Cable | Check router | Most reliable |
| WiFi | Check router | May need USB setup first |

## Login Credentials

- **Username**: `recamera`
- **Password**: `recamera` or `recamera.2`

## Step 1: Enable People Detection {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

Install the person detection program on reCamera so it can identify people in the video.

### Target: High Accuracy (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

More accurate detection, suitable for most scenarios.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | Check IP address and network |
| Wrong password | Try `recamera` or `recamera.2` |
| Install failed | Restart the camera and try again |

### Target: Fast Mode (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

Lower accuracy but uses less resources. Choose this if camera runs slow.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | Check IP address and network |
| Wrong password | Try `recamera` or `recamera.2` |
| Install failed | Restart the camera and try again |

---

## Step 2: View Live Heatmap {#preview type=preview required=false config=devices/preview.yaml}

Click **Connect** to see the live video with heatmap overlay.

**Tip:** The heatmap builds up over time - wait a few minutes to see the effect.

---

## Preset: Data Dashboard {#grafana}

Save historical data and view traffic trends with charts over time.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera with person detection |
| reComputer R1100 | Runs Grafana dashboard + InfluxDB |

**What you'll get:**
- Historical people flow data with time-series charts
- Customizable Grafana dashboards
- Data export for further analysis

**Requirements:** Docker installed · Same network for all devices

## Network Requirements

Make sure reCamera and your computer are on the **same WiFi network**.

## Step 1: Start Data Dashboard {#backend type=docker_deploy required=true config=devices/backend.yaml}

Start the data storage and chart display services on your computer (or a dedicated server).

### Target: Run on This Computer {#backend_local config=devices/backend.yaml default=true}

Run the dashboard on your current computer.

### Prerequisites

- Docker Desktop installed and running
- At least 2GB free disk space

![Wiring](gallery/architecture.svg)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflict error | Close the program using port 8086 or 3000 |
| Docker not starting | Open Docker Desktop application |
| Stops after starting | Make sure you have at least 4GB RAM |

### Target: Run on Another Device {#backend_remote config=devices/backend_remote.yaml}

Run the dashboard on a reComputer R1100 for dedicated edge deployment.

### Before You Begin

1. Connect the target device to your network
2. Get the device's IP address
3. Get the login credentials (username and password)

### Connection Settings

| Field | Example |
|-------|---------|
| Device IP | 192.168.1.100 |
| Username | recomputer |
| Password | 12345678 |

![Wiring](gallery/architecture.svg)

---

## Step 2: Connect Camera to Dashboard {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

Tell reCamera where to send the traffic data.

Enter:
- **reCamera IP**: Your camera's IP address
- **Dashboard Server IP**: The computer running the dashboard (from Step 1)

Other settings are pre-configured, no need to change.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | Check that camera and server are on the same network |
| No data showing | Make sure Step 1 completed successfully |

---

## Step 3: Show Heatmap on Floor Plan (Optional) {#heatmap type=manual required=false}

Overlay the heatmap on your store's floor plan image.

### How to Do It

1. **Prepare Images**
   - Take a screenshot from reCamera
   - Get your store's floor plan image

2. **Run the Calibration Tool**
   - Run: `python calibration_tool.py`
   - Click 4 reference points on the camera image
   - Click the same 4 spots on your floor plan

3. **View the Result**
   - Run `python -m http.server 8080`
   - Open `http://localhost:8080` in browser

### Skip This If

You only want to see the camera-view heatmap in the dashboard.

---

# Deployment Complete

## All Done!

Your real-time heatmap system is now running.

### Access Points

| Service | URL |
|---------|-----|
| Data Dashboard | http://\<server-ip\>:3000 |

### Login

- Username: `admin`
- Password: `admin`

Dashboard is pre-configured. Just open it to see your data.

### Having Issues?

- **No data showing**: Check that reCamera is connected
- **Can't open dashboard**: Run `docker ps` to check if services are running
