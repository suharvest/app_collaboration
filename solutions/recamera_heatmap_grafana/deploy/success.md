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
