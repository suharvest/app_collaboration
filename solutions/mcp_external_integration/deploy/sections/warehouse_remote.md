# Remote Deployment

Deploy the warehouse management system to a remote device (reComputer, Raspberry Pi, etc.).

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

1. Open `http://<device-ip>:2125`
2. Register the first admin account
3. Create API key in **User Management** -> **API Key Management**
4. Copy the API key (format: `wh_xxxx...`) for MCP configuration
