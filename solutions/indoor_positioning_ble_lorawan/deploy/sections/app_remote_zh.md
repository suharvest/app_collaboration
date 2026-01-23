## 远程部署

通过 SSH 将室内定位应用程序部署到远程服务器。

### 开始之前

1. 将目标设备连接到网络
2. 获取设备 IP 地址
3. 获取 SSH 凭据（用户名/密码）
4. 确保远程服务器已安装 Docker

### 部署完成后

1. 访问 `http://<设备IP>:5173`，默认账号 `admin` / `83EtWJUbGrPnQjdCqyKq`
2. 上传楼层地图，在地图上标记信标位置（输入 MAC 地址）
3. 配置 LoRaWAN 网络服务器 webhook 指向 `http://<设备IP>:5173/api/webhook`
