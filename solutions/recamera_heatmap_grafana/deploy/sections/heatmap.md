## Heatmap Calibration and Configuration

The heatmap page displays real-time foot traffic visualization on your floor plan.

### Step 1: Capture Reference Image from reCamera

1. In reCamera Node-RED workspace, stop the running program
2. Drag a **capture** node and connect it after the **camera** node
3. Configure the capture node:
   - Interval: 2000 (2 seconds)
   - Save to: /userdata/Images/
4. Click **Deploy** and **Run**
5. Wait 3-4 seconds, then click **Stop**

### Step 2: Download Images to Computer

1. Go to reCamera **Settings** > **Terminal**
2. Login with your reCamera credentials
3. Run:
```bash
cd /userdata/Images/
ls
```
4. On your computer, download using SCP:
```bash
scp -r recamera@<reCamera-IP>:/userdata/Images ./
```

### Step 3: Prepare Floor Plan

Draw or use an existing floor plan image of the area you want to monitor.

### Step 4: Run Calibration Tool

1. Download the project from [GitHub](https://github.com/xr686/reCamera-with-Heatmap)
2. Install OpenCV: `pip install opencv-python`
3. Place your camera image as `R1.jpg` and floor plan as `R2.png`
4. Run: `python calibration_tool.py`
5. Click 4 corners on camera image (clockwise: top-left, top-right, bottom-right, bottom-left)
6. Press any key
7. Click corresponding 4 corners on floor plan
8. Press any key
9. Copy the generated JavaScript code

### Step 5: Configure Heatmap HTML

Edit `index.html` in the heatmap-demo folder:

1. **Background Image**: Update to your floor plan filename
2. **Database Config**:
   - URL: Your InfluxDB URL
   - ORG: Your InfluxDB username
   - BUCKET: Your bucket name (recamera)
   - TOKEN: Your InfluxDB API token
3. **Camera Resolution**: Match your reCamera settings (e.g., 1920x1080)
4. **Calibration Data**: Paste the generated JavaScript code

### Step 6: Start Heatmap Server

```bash
cd heatmap-demo
python -m http.server 8080
```

Access the heatmap at http://localhost:8080/index.html
