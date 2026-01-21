## Grafana 安装和配置

Grafana 提供实时热力图和分析的可视化仪表板。

### 选项 A：Docker 部署（推荐）

如果您使用 Docker 部署了 InfluxDB，Grafana 已经在 http://localhost:3000 运行

默认凭据：
- 用户名：admin
- 密码：admin（首次登录时会提示更改）

### 选项 B：手动安装

#### Windows

1. 从 [grafana.com](https://grafana.com/get/) 下载 Grafana
2. 运行安装程序
3. Grafana 将作为 Windows 服务自动启动
4. 检查**服务**以验证其是否正在运行

#### Linux

ARM 设备：
```bash
wget https://dl.grafana.com/grafana/release/12.3.0/grafana_12.3.0_19497075765_linux_arm64.tar.gz
tar xvfz grafana_12.3.0_19497075765_linux_arm64.tar.gz
cd grafana-12.3.0
./bin/grafana-server
```

AMD64 设备：
```bash
wget https://dl.grafana.com/grafana/release/12.3.0/grafana_12.3.0_19497075765_linux_amd64.tar.gz
tar xvfz grafana_12.3.0_19497075765_linux_amd64.tar.gz
cd grafana-12.3.0
./bin/grafana-server
```

### 启用 HTML 嵌入

1. 导航到 `grafana/conf/defaults.ini`
2. 找到 `disable_sanitize_html`
3. 将 `false` 改为 `true`
4. 重启 Grafana 服务

### 配置数据源

1. 打开 Grafana：http://localhost:3000
2. 登录（admin/admin）
3. 进入 **Connections** > **Data sources** > **Add data source**
4. 选择 **InfluxDB**
5. 配置：
   - Query Language：**Flux**
   - URL：`http://localhost:8086`（或您的 InfluxDB URL）
   - 禁用 **Basic auth**
   - Organization：您的 InfluxDB 用户名
   - Token：您的 InfluxDB API 令牌
   - Default Bucket：recamera
6. 点击 **Save & Test**

### 导入仪表板

1. 进入 **Dashboards** > **New** > **Import**
2. 从 [GitHub](https://github.com/xr686/reCamera-with-Heatmap) 下载仪表板 JSON
3. 上传 `reCamera Heatmap-1766213863140.json`
4. 选择您的 InfluxDB 数据源
5. 点击 **Import**
