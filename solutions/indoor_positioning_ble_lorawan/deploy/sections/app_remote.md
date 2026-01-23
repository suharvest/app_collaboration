## Remote Deployment

Deploy the indoor positioning application to a remote server via SSH.

### Before You Begin

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### After Deployment

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`
