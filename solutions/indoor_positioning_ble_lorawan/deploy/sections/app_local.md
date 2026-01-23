## Local Deployment

Deploy the indoor positioning application on your local computer.

### Requirements

- Docker Desktop installed and running
- Port 5173 available

### After Deployment

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`
