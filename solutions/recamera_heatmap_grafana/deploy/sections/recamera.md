## Configure reCamera

Set up reCamera to send detected traffic data to the database.

### Steps

1. Visit [SenseCraft reCamera](https://sensecraft.seeed.cc/ai/recamera) and deploy the heatmap app to your reCamera
2. Open reCamera's Node-RED interface and install the `node-red-contrib-influxdb` node
3. Configure the database node:
   - URL: `http://<your-computer-ip>:8086`
   - Paste the API token from the previous step
4. Click Deploy to activate the flow

