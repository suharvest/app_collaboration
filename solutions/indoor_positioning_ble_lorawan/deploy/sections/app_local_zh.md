## 本机部署

将室内定位应用程序部署到您的本地电脑。

### 前提条件

- Docker Desktop 已安装并运行
- 端口 5173 可用

### 部署完成后

1. 访问 `http://localhost:5173`，默认账号 `admin` / `83EtWJUbGrPnQjdCqyKq`
2. 上传楼层地图，在地图上标记信标位置（输入 MAC 地址）
3. 配置 LoRaWAN 网络服务器 webhook 指向 `http://本机IP:5173/api/webhook`
