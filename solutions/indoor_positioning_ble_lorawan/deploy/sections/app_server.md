## Application Server Deployment

The positioning application provides a web dashboard for configuring beacons, viewing maps, and tracking devices.

### System Requirements

- Docker installed and running
- Port 5173 available
- Minimum 1GB RAM recommended

### What Gets Deployed

The Docker container includes:
- **Web Dashboard** - Configure maps, beacons, and view live positions
- **Backend API** - Handles webhook data from LoRaWAN network server
- **SQLite Database** - Stores beacon and tracker configurations

### Post-Deployment Configuration

After deployment, you'll need to:

1. **Login to dashboard** at `http://localhost:5173`
   - Default username: `admin`
   - Default password: `83EtWJUbGrPnQjdCqyKq`

2. **Configure network server webhook**
   - In SenseCraft Data or ChirpStack, set up an HTTP integration
   - Point webhook URL to `http://YOUR_SERVER_IP:5173/api/webhook`

3. **Upload floor map**
   - Navigate to Map settings
   - Upload your floor plan image
   - Set the map scale (pixels per meter)

4. **Add beacon positions**
   - Click on the map to add beacon markers
   - Enter the beacon MAC address for each position

### Data Persistence

All data is stored in mounted volumes:
- `./db` - SQLite database
- `./config` - Configuration files
- `./uploads` - Uploaded map images
