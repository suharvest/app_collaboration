## Tracker Configuration

The SenseCAP T1000 tracker is the mobile device that reports its position based on nearby BLE beacons.

### Activation Steps

1. **Power on** - Press and hold the power button for 3 seconds
2. **LED indicator** - Green flash indicates LoRaWAN join attempt
3. **Successful join** - Solid green LED briefly, then LED turns off

### Configuration via SenseCraft App

1. Download **SenseCraft App** from App Store or Google Play
2. Enable Bluetooth on your phone
3. Press the tracker button once to enable BLE pairing
4. In the app, scan for nearby devices and select your T1000
5. Configure the following settings:

**Work Mode**
- Select "BLE Scan" mode for indoor positioning
- This enables the tracker to scan for nearby beacons

**Positioning Settings**
- **BLE Scan Interval**: How often to scan (default: 5 minutes)
- **Motion Trigger**: Enable to scan only when moving (saves battery)
- **Report Interval**: How often to send data via LoRaWAN

**LoRaWAN Settings**
- **Region**: Match your gateway's frequency plan (US915, EU868, etc.)
- **Join Mode**: OTAA recommended
- **Network Server**: Select SenseCraft Data or enter custom server details

### Verify Tracker Operation

After configuration:
1. Walk near a BLE beacon
2. Press the tracker button to trigger an immediate report
3. Check the positioning dashboard to see the tracker appear on the map

### Battery Life Tips

- Enable motion trigger to avoid unnecessary scans
- Increase scan interval if real-time tracking isn't needed
- Typical battery life: 3-6 months depending on settings
