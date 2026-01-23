# Remote Deployment

Deploy InfluxDB and Grafana to a remote device (reComputer, Raspberry Pi, etc.).

## Before You Begin

1. **Connect target device to the network**
   - Ensure the device is on the same network as your computer
   - Note down the device's IP address

2. **Get device credentials**
   - SSH username (usually `root`, `pi`, or `recomputer`)
   - SSH password

## Connection Settings

Enter the following information:

| Field | Description | Example |
|-------|-------------|---------|
| Device IP | Target device IP address | 192.168.1.100 |
| SSH Username | Login username | root |
| SSH Password | Login password | your-password |
| SSH Port | SSH port (default 22) | 22 |

## After Deployment

Access InfluxDB: `http://<device-ip>:8086`
- Credentials: admin / adminpassword
- Organization: seeed, Bucket: recamera

Go to **API Tokens** and copy the token for later configuration.

Access Grafana: `http://<device-ip>:3000`
- Default credentials: admin / admin
