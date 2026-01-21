## reCamera Configuration

Configure reCamera to run person detection and send data to InfluxDB.

### Step 1: Install the Application from SenseCraft

1. Go to [SenseCraft reCamera Workspace](https://sensecraft.seeed.cc/ai/recamera)
2. Find the demo named **"Real-time heat map local blur processing Grafana"**
3. Deploy it to your reCamera

### Step 2: Connect to Network

1. In the reCamera workspace, connect to your WiFi network
2. **Important**: Ensure reCamera is on the same network as your computer running InfluxDB

### Step 3: Install Missing Node

1. After entering the workspace, you'll see a warning about missing nodes - click **Close**
2. Go to the menu (top-right hamburger icon) > **Manage palette**
3. Click **Install** tab
4. Search for `node-red-contrib-influxdb`
5. Install version **0.7.0**
6. Wait for installation to complete

### Step 4: Configure InfluxDB Node

1. Find the **"Write Person Count"** node in the flow
2. Double-click to open configuration
3. Click the pencil icon next to **Server**
4. Configure:
   - **URL**: `http://<your-computer-ip>:8086`
   - **Token**: Paste your InfluxDB API token
5. Click **Update**
6. Click **Deploy** (top-right)

### Step 5: Verify Data Flow

1. Open InfluxDB UI at `http://<your-ip>:8086`
2. Go to **Data Explorer**
3. Select your bucket (recamera)
4. Click **Submit** to query data
5. You should see data appearing as a line graph
