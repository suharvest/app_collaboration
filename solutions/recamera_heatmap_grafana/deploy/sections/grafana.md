## Grafana Installation and Configuration

Grafana provides the visualization dashboard for real-time heatmap and analytics.

### Option A: Docker Deployment (Recommended)

If you used Docker for InfluxDB, Grafana is already running at http://localhost:3000

Default credentials:
- Username: admin
- Password: admin (you'll be prompted to change on first login)

### Option B: Manual Installation

#### Windows

1. Download Grafana from [grafana.com](https://grafana.com/get/)
2. Run the installer
3. Grafana will start automatically as a Windows service
4. Check **Services** to verify it's running

#### Linux

For ARM devices:
```bash
wget https://dl.grafana.com/grafana/release/12.3.0/grafana_12.3.0_19497075765_linux_arm64.tar.gz
tar xvfz grafana_12.3.0_19497075765_linux_arm64.tar.gz
cd grafana-12.3.0
./bin/grafana-server
```

For AMD64 devices:
```bash
wget https://dl.grafana.com/grafana/release/12.3.0/grafana_12.3.0_19497075765_linux_amd64.tar.gz
tar xvfz grafana_12.3.0_19497075765_linux_amd64.tar.gz
cd grafana-12.3.0
./bin/grafana-server
```

### Enable HTML Embedding

1. Navigate to `grafana/conf/defaults.ini`
2. Find `disable_sanitize_html`
3. Change from `false` to `true`
4. Restart Grafana service

### Configure Data Source

1. Open Grafana at http://localhost:3000
2. Login (admin/admin)
3. Go to **Connections** > **Data sources** > **Add data source**
4. Select **InfluxDB**
5. Configure:
   - Query Language: **Flux**
   - URL: `http://localhost:8086` (or your InfluxDB URL)
   - Disable **Basic auth**
   - Organization: your InfluxDB username
   - Token: your InfluxDB API token
   - Default Bucket: recamera
6. Click **Save & Test**

### Import Dashboard

1. Go to **Dashboards** > **New** > **Import**
2. Download the dashboard JSON from [GitHub](https://github.com/xr686/reCamera-with-Heatmap)
3. Upload `reCamera Heatmap-1766213863140.json`
4. Select your InfluxDB data source
5. Click **Import**
