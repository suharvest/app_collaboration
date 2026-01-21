### 配置 reCamera

1. 访问 [SenseCraft reCamera](https://sensecraft.seeed.cc/ai/recamera)，部署热力图应用到 reCamera
2. 在 Node-RED 中安装 `node-red-contrib-influxdb` 节点
3. 配置 InfluxDB 节点：URL 填 `http://<服务器IP>:8086`，粘贴 Token
4. 点击 Deploy，检查 InfluxDB Data Explorer 有数据
