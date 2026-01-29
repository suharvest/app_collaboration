## Deployment Successful!

Your HVAC Automation Control System is now running.

### Next Steps

1. **Access the Web Interface** - Open your browser and navigate to the application URL
2. **Connect to OPC-UA Server** - Configure your OPC-UA server connection or use the built-in simulator
3. **Upload Training Data** - Import your historical HVAC data for model training
4. **Configure Parameters** - Set up input/output parameter mappings

### Useful Commands

Check container status:
```bash
docker ps | grep missionpack_knn
```

View application logs:
```bash
docker logs missionpack_knn
```

Restart the application:
```bash
docker restart missionpack_knn
```

### Kiosk Mode (Optional)

You can configure Kiosk mode from the Devices management page to auto-start the application in fullscreen on boot.
