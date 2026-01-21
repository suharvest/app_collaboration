## Kiosk Mode Configuration

Kiosk mode allows the HVAC control interface to automatically start in fullscreen when the device boots up.

### What is Kiosk Mode?

- Automatically launches the web application on system startup
- Displays the interface in fullscreen without browser controls
- Disables screen saver and power management
- Ideal for dedicated control stations or monitoring displays

### Configuration

After deployment, you can enable or disable Kiosk mode from the **Devices** management page:

1. Navigate to the Devices page
2. Find your deployed application
3. Toggle the Kiosk switch
4. Select the system user account to run Kiosk mode
5. The configuration will be applied automatically

### Requirements

- A desktop environment installed on the device
- Chromium or Firefox browser installed
- A system user account for running Kiosk mode

### Manual Configuration

If you prefer to configure manually via SSH:

**Enable Kiosk Mode:**
```bash
./configure_kiosk.sh <username> http://localhost:8280
```

**Disable Kiosk Mode:**
```bash
./unconfigure_kiosk.sh <username>
```

After configuration, reboot the device to apply changes.
