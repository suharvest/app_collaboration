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
