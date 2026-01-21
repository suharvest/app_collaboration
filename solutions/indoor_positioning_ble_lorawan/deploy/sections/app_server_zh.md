## 应用服务器部署

定位应用程序提供 Web 仪表板，用于配置信标、查看地图和追踪设备。

### 系统要求

- 已安装并运行 Docker
- 端口 5173 可用
- 建议至少 1GB RAM

### 部署内容

Docker 容器包含：
- **Web 仪表板** - 配置地图、信标和查看实时位置
- **后端 API** - 处理来自 LoRaWAN 网络服务器的 webhook 数据
- **SQLite 数据库** - 存储信标和追踪器配置

### 部署后配置

部署后，您需要：

1. **登录仪表板** `http://localhost:5173`
   - 默认用户名：`admin`
   - 默认密码：`83EtWJUbGrPnQjdCqyKq`

2. **配置网络服务器 webhook**
   - 在 SenseCraft Data 或 ChirpStack 中设置 HTTP 集成
   - 将 webhook URL 指向 `http://您的服务器IP:5173/api/webhook`

3. **上传楼层地图**
   - 导航到地图设置
   - 上传您的楼层平面图
   - 设置地图比例（每米像素数）

4. **添加信标位置**
   - 点击地图添加信标标记
   - 为每个位置输入信标 MAC 地址

### 数据持久化

所有数据存储在挂载的卷中：
- `./db` - SQLite 数据库
- `./config` - 配置文件
- `./uploads` - 上传的地图图像
