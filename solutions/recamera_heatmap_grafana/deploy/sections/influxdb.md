## InfluxDB Installation

InfluxDB is a high-performance time-series database that stores the detection coordinates from reCamera.

### Option A: Docker Deployment (Recommended)

Click the **Deploy** button above to automatically deploy InfluxDB using Docker Compose.

After deployment:
1. Access InfluxDB at http://localhost:8086
2. Default credentials: admin / adminpassword
3. Organization: seeed
4. Bucket: recamera

### Option B: Manual Installation

#### Windows

1. Download InfluxDB from [influxdata.com](https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-windows-amd64.zip)
2. Extract the archive
3. Open Command Prompt and navigate to the extracted directory
4. Run: `influxd`

#### Linux

For ARM devices (like Raspberry Pi):
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-linux-arm64.tar.gz
tar xvfz influxdb2-2.1.1-linux-arm64.tar.gz
cd influxdb2-2.1.1
./influxd
```

For AMD64 devices:
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-linux-amd64.tar.gz
tar xvfz influxdb2-2.1.1-linux-amd64.tar.gz
cd influxdb2-2.1.1
./influxd
```

### Initial Configuration

1. Open browser and go to `http://<your-ip>:8086`
2. Click **Get Started**
3. Fill in your information:
   - Username: your choice (remember this!)
   - Password: your choice (remember this!)
   - Organization: seeed (or your preference)
   - Bucket Name: recamera
4. Click **Configure Later**
5. Go to **Data** to verify your bucket
6. Go to **API Tokens** and copy your token for later use
