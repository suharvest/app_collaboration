## Configure Dashboard

Connect the database to Grafana and import the pre-built chart templates.

### Steps

1. Open your browser and go to `http://localhost:3000`
2. Log in with default credentials: admin / admin
3. Add data source:
   - Go to **Connections** > **Data sources** > click **Add data source**
   - Select **InfluxDB**
   - Set Query Language to **Flux**
   - URL: `http://influxdb:8086`
   - Paste your API token
   - Click **Save & Test**
4. Import chart templates:
   - Go to **Dashboards** > **Import**
   - Upload the dashboard JSON file provided with this solution

