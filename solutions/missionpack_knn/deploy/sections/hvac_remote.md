## Remote Deployment

Deploy the HVAC Automation Control System to a remote device via SSH.

### Target Device Requirements

- Linux-based system (Ubuntu, Debian, etc.)
- Docker installed and running
- SSH access enabled
- Ports 8280 and 4841 available

### Connection Details

- **Device IP**: The IP address of your remote device
- **SSH Username**: Login username (default: recomputer)
- **SSH Password**: Login password

### What Will Be Deployed

The deployment process will:
1. Connect to the remote device via SSH
2. Create deployment directory at `/home/<user>/missionpack_knn`
3. Upload Docker Compose files
4. Pull the container image
5. Start the application service

### After Deployment

The application will be available at **http://<device-ip>:8280**

You can also configure Kiosk mode to automatically start the application in fullscreen on boot.
