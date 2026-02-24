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
3. Username `recamera`, default password `recamera` (use your own if changed)

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
3. Username `recamera`, default password `recamera` (use your own if changed)

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

## Preset: Home Assistant Integration {#ha_integration}

Connect reCamera to Home Assistant for unified smart home monitoring.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera with YOLO detection + RTSP streaming |
| Computer or reComputer R1100 | Runs Home Assistant |

**What you'll get:**
- Live RTSP video stream as an HA camera entity
- AI detection count sensor with per-class breakdown (person, car, etc.)
- FlowFuse Dashboard on reCamera for local debugging

**Requirements:** Docker installed · Same local network for all devices

---

## Step 1: Deploy Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant.yaml}

Start Home Assistant. Skip this step if you already have HA running.

### Target: Run on This Computer {#ha_local type=local config=devices/homeassistant.yaml default=true}

### Wiring

1. Make sure Docker Desktop is installed and running
2. Ensure at least 2GB free disk space

### Deployment Complete

1. Open **http://localhost:8123** in your browser
2. Follow the onboarding wizard to create your admin account
3. Remember your username and password — you'll need them in Step 3

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 busy | Close the program using port 8123, or change the port in docker-compose.yml |
| Docker not starting | Open Docker Desktop application |
| Container keeps restarting | Make sure you have at least 2GB RAM available |

### Target: Run on Remote Device {#ha_remote type=remote config=devices/homeassistant_remote.yaml}

### Wiring

1. Connect the target device to the network
2. Enter IP address, username and password below

### Deployment Complete

1. Open **http://\<device-ip\>:8123** in your browser
2. Follow the onboarding wizard to create your admin account
3. Remember your username and password — you'll need them in Step 3

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network cable, test with ping |
| SSH authentication failed | Verify username and password |

---

## Step 2: Deploy AI Detection Flow {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

Install YOLO detection + RTSP streaming flow on reCamera.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 3: Add reCamera to Home Assistant {#configure_ha type=ha_integration required=true config=devices/homeassistant_existing.yaml}

Install the reCamera integration and connect it to Home Assistant.

### Wiring

1. Enter your Home Assistant **IP address** (e.g. `192.168.1.100`)
2. Enter the **HA login username and password** you created during HA setup
3. Enter the **reCamera IP address** — use `192.168.42.1` if connected via USB, or the WiFi IP from your router
4. **HA OS users**: leave the SSH fields empty — the system will set up SSH automatically
5. **Docker HA users**: fill in the SSH username and password of the **host machine** (not the HA login)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| HA login failed | The username and password here are for HA web login, not SSH. Check they are correct |
| Restart takes a long time | HA OS restarts the entire system — this can take 30-90 seconds, please wait |
| SSH addon install failed | HA OS needs internet to download the SSH addon. Check network connectivity |
| File copy failed | HA OS: check disk space. Docker: verify SSH credentials are for the **host machine** |
| `setup_retry` after adding | HA cannot reach reCamera — make sure both devices are on the same network |
| Camera thumbnail blank, but stream works | Known issue: ffmpeg snapshot may time out; the live stream in the dashboard works fine |
| Sensor shows 0 | Normal when nothing is in view; verify at http://\<recamera-ip\>:1880/data |

### Deployment Complete

Your reCamera is now integrated with Home Assistant!

## Quick Verification

1. Open **http://\<server-ip\>:8123**
2. Go to **Settings → Devices & Services** — you should see **reCamera (your-ip)** listed
3. Click into the device to see both entities
4. Add a **Picture Entity** card to your dashboard for the camera stream

## Access Points

- **Home Assistant**: http://\<server-ip\>:8123 — your unified smart home dashboard
- **FlowFuse Dashboard**: http://\<recamera-ip\>:1880/dashboard — local debugging UI on reCamera
- **Detection API**: http://\<recamera-ip\>:1880/data — raw detection JSON data

## Next Steps

- Create **automations** using the detection sensor (e.g. turn on lights when person count > 0)
- Add the camera to a **dashboard card** with Picture Entity or Picture Glance
- Set up **mobile notifications** when specific objects are detected

**Having issues?**
- No video? Check reCamera IP and that Step 2 completed successfully
- No detection data? Make sure objects are in view; check Node-RED at http://\<recamera-ip\>:1880

---

## Preset: OCR Text Reader {#ocr_reader}

Point reCamera at any text — signs, labels, meter displays — and the recognized characters appear on screen in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that reads text from the video |

**What you'll get:**
- Live video with recognized text highlighted on screen
- Works with printed text, signs, labels, and digital displays
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Text Recognition {#deploy_ppocr type=recamera_cpp required=true config=devices/recamera_ppocr.yaml}

Install the text recognition program on reCamera so it can read text in the video.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View OCR Overlay {#preview_ocr type=preview required=false config=devices/preview_ocr.yaml}

Click **Connect** to see the live video with OCR text overlay.

**Tip:** Point the camera at text — signs, labels, screens — for best results.

**Note:** Video preview requires ffmpeg. Open a terminal and install it:
- **Windows:** Open PowerShell, run `winget install ffmpeg`
- **macOS:** Open Terminal, run `brew install ffmpeg`
- **Linux:** Open Terminal, run `sudo apt install ffmpeg`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No text detected | Make sure text is clearly visible and well-lit; check Step 1 completed |
| ffmpeg error | Install ffmpeg using the commands above for your OS |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live OCR overlay.

Point the camera at printed text — the recognized characters will appear above each detected region.

---

## Preset: Face Analysis {#face_analysis}

Point reCamera at people — it detects faces and analyzes age, gender, and emotion in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that analyzes faces in the video |

**What you'll get:**
- Live video with face bounding boxes and analysis labels
- Age, gender, and emotion displayed for each detected face
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Face Analysis {#deploy_face_analysis type=recamera_cpp required=true config=devices/recamera_face_analysis.yaml}

Install the face analysis program on reCamera so it can detect faces and analyze age, gender, and emotion.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Face Analysis Results {#preview_face_analysis type=preview required=false config=devices/preview_face_analysis.yaml}

Click **Connect** to see the live video with face analysis overlay.

**Tip:** Point the camera at people — each detected face will show age, gender, and emotion.

**Note:** Video preview requires ffmpeg. Open a terminal and install it:
- **Windows:** Open PowerShell, run `winget install ffmpeg`
- **macOS:** Open Terminal, run `brew install ffmpeg`
- **Linux:** Open Terminal, run `sudo apt install ffmpeg`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No faces detected | Make sure faces are clearly visible and well-lit; check Step 1 completed |
| ffmpeg error | Install ffmpeg using the commands above for your OS |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live face analysis overlay.

Each detected face will show age, gender, and emotion — all analyzed on-device in real-time.
