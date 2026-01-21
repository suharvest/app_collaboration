## Real-time Heatmap Preview

View live video with people detection and heatmap overlay directly in your browser.

### How It Works

1. **Video Stream** - RTSP video is proxied to your browser via HLS
2. **MQTT Data** - Detection results are received via WebSocket
3. **Heatmap Overlay** - Canvas overlay renders the heatmap and tracking info

### Using the Preview

1. Enter the reCamera IP address (same as deployment step)
2. Click **Connect** to start the preview
3. The heatmap will build up over time as people are detected

### Understanding the Display

#### Heatmap Colors
- **Blue** - Low activity (brief passes)
- **Green** - Moderate activity
- **Yellow** - High activity
- **Red** - Hotspots (people spend significant time here)

#### Person States
- **Gray box** - Moving through
- **Blue box** - Browsing
- **Amber box** - Engaged (showing interest)
- **Red box** - May need assistance (long dwell)

### Stats Panel

The stats panel shows:
- **Total** - Number of people currently detected
- **Browsing** - People browsing (short dwell)
- **Engaged** - People showing interest (1.5-20s dwell)
- **Need Help** - People who may need assistance (>20s dwell)

### Tips

- The heatmap accumulates over time - give it a few minutes to build up
- Hot zones indicate where customers spend the most time
- Use this data to optimize product placement and staffing
