### Configure Heatmap

1. Export camera screenshot from reCamera, prepare floor plan image
2. Run calibration tool: `python calibration_tool.py`, click 4 corresponding points on both images
3. Paste generated calibration code into `index.html`, configure InfluxDB connection
4. Start server: `python -m http.server 8080`, visit `http://localhost:8080`
