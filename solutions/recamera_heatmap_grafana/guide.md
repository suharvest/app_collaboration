## Preset: Quick Preview {#simple}

Just one reCamera - view heatmap directly in its web interface.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that detects people in the video |

**What you'll get:**
- Live video with heatmap overlay (heatmap generated in real-time by the web interface)
- See busy vs quiet areas in real-time
- Privacy protection (faces auto-blurred)

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Enable People Detection {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

Install the person detection program on reCamera so it can identify people in the video.

### Target: YOLO11 (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

Recommended for most scenarios.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Enter username `recamera`, password `recamera`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

### Target: YOLOv26 (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

Alternative model, try if needed.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Enter username `recamera`, password `recamera`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Live Heatmap {#preview type=preview required=false config=devices/preview.yaml}

Click **Connect** to see the live video with heatmap overlay.

**Tip:** The heatmap builds up over time - wait a few minutes to see the effect.

**Note:** Heatmap rendering requires ffmpeg. Open a terminal and install it:
- **Windows:** Open PowerShell, run `winget install ffmpeg`
- **macOS:** Open Terminal, run `brew install ffmpeg`
- **Linux:** Open Terminal, run `sudo apt install ffmpeg`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No heatmap overlay | Wait a few minutes for data to accumulate; make sure Step 1 completed |
| ffmpeg error | Install ffmpeg using the commands above for your OS |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live heatmap.

The heatmap builds up over time - areas where people stay longer will glow brighter.

---

## Preset: Data Dashboard {#grafana}

Add a computer to run the dashboard - save history and view traffic trends over time.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that detects people and sends location data |
| Computer or reComputer R1100 | Runs Grafana dashboard + InfluxDB |

**What you'll get:**
- View daily/weekly traffic trends with charts
- Customize dashboard layout
- Export data for analysis

**Requirements:** Docker installed · Same network for all devices

## Step 1: Start Data Dashboard {#backend type=docker_deploy required=true config=devices/backend.yaml}

Start the data storage and chart display services on your computer (or a dedicated server).

### Target: Run on This Computer {#backend_local type=local config=devices/backend.yaml default=true}

### Wiring

![Wiring](gallery/architecture.svg)

Make sure Docker Desktop is installed and running, with at least 2GB free disk space.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflict error | Close the program using port 8086 or 3000 |
| Docker not starting | Open Docker Desktop application |
| Stops after starting | Make sure you have at least 4GB RAM |

### Target: Run on Another Device {#backend_remote type=remote config=devices/backend_remote.yaml}

### Wiring

![Wiring](gallery/architecture.svg)

| Field | Example |
|-------|---------|
| Device IP | 192.168.1.100 or reComputer-R110x.local |
| Username | recomputer |
| Password | 12345678 |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network cable, test with ping |
| SSH authentication failed | Verify username and password |

---

## Step 2: Connect Camera to Dashboard {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

Tell reCamera where to send the traffic data.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Enter reCamera IP and Dashboard Server IP (from Step 1)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| No data showing | Make sure Step 1 completed; camera and server on same network |

---

## Step 3: Map Heatmap to Floor Plan (Optional) {#heatmap type=manual required=false}

By default, the heatmap shows the camera's perspective. To display it on your store's actual floor plan, use the built-in calibration tool.

### How to Do It

1. Open **http://\<server-ip\>:8080** in your browser
2. Click the **gear icon** (top-right corner) to open calibration settings
3. Upload a **camera screenshot** (left side) and your **floor plan image** (right side)
4. Click **4 matching reference points** on the camera view, then the same 4 spots on the floor plan
5. Click **Save** — calibration is applied immediately

**Tips:** Choose widely-spaced landmarks like corners, pillars, or doorways as reference points.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Heatmap doesn't align well | Re-open settings, click Reset, and recalibrate with better reference points |
| Calibration lost after clearing browser data | Open settings and recalibrate — settings are stored in your browser |

### Skip This If

You only want to see the camera-view heatmap without mapping to a floor plan.

### Deployment Complete

Your heatmap dashboard is ready!

**Access your services:**
- **Data Dashboard**: http://\<server-ip\>:3000 — login `admin` / `admin`, view traffic charts and trends
- **Live Heatmap**: http://\<server-ip\>:8080 — real-time heatmap overlay (calibrate via gear icon)

Both services start automatically with Step 1.

**Having issues?**
- No data? Check that reCamera is connected (Step 2)
- Can't open pages? Run `docker ps` to check services are running
