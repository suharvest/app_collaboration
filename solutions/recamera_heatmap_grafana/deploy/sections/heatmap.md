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

