## BLE Beacon Deployment Guide

BLE beacons are the foundation of indoor positioning. Proper placement ensures accurate location tracking.

### Placement Guidelines

**For Triangulation Mode (Recommended)**
- Deploy at least 3 beacons per area
- Place beacons at ceiling height (2.5-3m)
- Maintain 10-15m spacing between beacons
- Avoid metal obstructions near beacons

**For Proximity Mode**
- Deploy 1-2 beacons per zone
- Place at entrance/exit points
- Adjust TX power to define zone radius

### Installation Steps

1. **Plan beacon locations** - Draw a floor plan and mark beacon positions
2. **Install beacons** - Mount using adhesive or screws at marked locations
3. **Record MAC addresses** - Note down each beacon's MAC address and its physical location
4. **Test coverage** - Walk around with a BLE scanner app to verify signal coverage

### Beacon Configuration

BC01 beacons come pre-configured, but you can adjust settings using the **SenseCraft App**:
- **TX Power** - Higher power = longer range but shorter battery life
- **Advertising Interval** - Shorter interval = faster detection but shorter battery life
- **UUID/Major/Minor** - Used for beacon identification

### Tips for Best Results

- Keep beacons away from metal surfaces and water pipes
- For multi-floor buildings, deploy beacons on each floor
- Create a beacon inventory spreadsheet with MAC addresses and locations
