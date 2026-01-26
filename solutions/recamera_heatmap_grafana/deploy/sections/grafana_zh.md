## 配置数据看板

将数据库连接到 Grafana 数据看板，导入预设的图表模板。

### 操作步骤

1. 打开浏览器访问 `http://localhost:3000`
2. 使用默认账号登录：admin / admin
3. 添加数据源：
   - 进入 **Connections** > **Data sources** > 点击 **Add data source**
   - 选择 **InfluxDB**
   - Query Language 选择 **Flux**
   - URL 填写 `http://influxdb:8086`
   - 粘贴之前复制的 API 令牌
   - 点击 **Save & Test**
4. 导入图表模板：
   - 进入 **Dashboards** > **Import**
   - 上传方案提供的仪表板 JSON 文件

