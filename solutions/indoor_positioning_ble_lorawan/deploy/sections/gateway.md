## LoRaWAN Gateway Setup

The LoRaWAN gateway receives data from trackers and forwards it to your network server.

### SenseCAP M2 Gateway Setup

1. **Power on** - Connect the gateway to power using the included adapter
2. **Connect to network** - Use Ethernet cable or configure WiFi via SenseCraft App
3. **Wait for initialization** - The LED will turn solid green when ready

### Network Server Options

Choose one of the following options to receive tracker data:

**Option A: SenseCraft Data Platform (Recommended for beginners)**
1. Download the SenseCraft App
2. Scan the QR code on your gateway
3. Follow the setup wizard to bind the gateway
4. Your gateway will automatically connect to SenseCraft Data

**Option B: ChirpStack (Self-hosted)**
1. Set up a ChirpStack server instance
2. Access gateway web interface at its IP address
3. Configure the Network Server settings to point to your ChirpStack
4. Add the gateway in ChirpStack using the Gateway EUI

### Verify Gateway Status

- **SenseCraft Data**: Check gateway status in the app or web portal
- **ChirpStack**: Navigate to Gateways and verify "Last seen" timestamp

### Coverage Tips

- Place gateway at a central, elevated location
- Avoid placing near metal enclosures or thick walls
- One gateway typically covers a 2km radius indoors
