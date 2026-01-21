### 部署完成后

1. 访问 `http://localhost:3000`，账号 admin/admin
2. **Connections** > **Data sources** > 添加 InfluxDB
   - Query Language: Flux
   - URL: `http://influxdb:8086`
   - Token: 粘贴 InfluxDB API 令牌
3. **Dashboards** > **Import** > 上传仪表板 JSON
