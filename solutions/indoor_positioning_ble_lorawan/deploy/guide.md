## Before You Begin

Ensure you have the following hardware components ready:

- **SenseCAP T1000 Tracker** - At least one unit for testing
- **BC01 BLE Beacons** - 3+ beacons for triangulation, or 1+ for proximity mode
- **SenseCAP M2 Gateway** - Or any compatible LoRaWAN gateway
- **A computer** with Docker installed for running the positioning server

## Deployment Overview

This deployment consists of four steps:

1. **Deploy BLE Beacons** - Install beacons at strategic locations and record their positions
2. **Setup LoRaWAN Gateway** - Connect gateway to your network server
3. **Deploy Positioning Application** - One-click Docker deployment
4. **Configure Tracker** - Activate and connect your T1000 tracker

## After Deployment

Once all steps are completed:

1. Access the dashboard at `http://localhost:5173`
2. Login with default credentials:
   - Username: `admin`
   - Password: `83EtWJUbGrPnQjdCqyKq`
3. Upload your floor map and configure beacon positions
4. Start tracking your devices!
