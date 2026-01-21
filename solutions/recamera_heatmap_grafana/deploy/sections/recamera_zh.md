## reCamera 配置

配置 reCamera 运行人员检测并向 InfluxDB 发送数据。

### 第一步：从 SenseCraft 安装应用

1. 访问 [SenseCraft reCamera 工作区](https://sensecraft.seeed.cc/ai/recamera)
2. 找到名为 **"Real-time heat map local blur processing Grafana"** 的演示
3. 将其部署到您的 reCamera

### 第二步：连接网络

1. 在 reCamera 工作区中，连接到您的 WiFi 网络
2. **重要**：确保 reCamera 与运行 InfluxDB 的电脑在同一网络

### 第三步：安装缺失的节点

1. 进入工作区后，您会看到关于缺失节点的警告 - 点击 **Close**
2. 进入菜单（右上角汉堡图标）> **Manage palette**
3. 点击 **Install** 标签
4. 搜索 `node-red-contrib-influxdb`
5. 安装版本 **0.7.0**
6. 等待安装完成

### 第四步：配置 InfluxDB 节点

1. 在流程中找到 **"Write Person Count"** 节点
2. 双击打开配置
3. 点击 **Server** 旁边的铅笔图标
4. 配置：
   - **URL**：`http://<您的电脑IP>:8086`
   - **Token**：粘贴您的 InfluxDB API 令牌
5. 点击 **Update**
6. 点击 **Deploy**（右上角）

### 第五步：验证数据流

1. 打开 InfluxDB 界面：`http://<您的IP>:8086`
2. 进入 **Data Explorer**
3. 选择您的存储桶（recamera）
4. 点击 **Submit** 查询数据
5. 您应该能看到数据以折线图形式出现
