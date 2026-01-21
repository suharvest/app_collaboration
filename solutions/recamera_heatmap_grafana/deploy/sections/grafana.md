### After Deployment

1. Visit `http://localhost:3000`, login with admin/admin
2. **Connections** > **Data sources** > Add InfluxDB
   - Query Language: Flux
   - URL: `http://influxdb:8086`
   - Token: paste InfluxDB API token
3. **Dashboards** > **Import** > upload dashboard JSON
