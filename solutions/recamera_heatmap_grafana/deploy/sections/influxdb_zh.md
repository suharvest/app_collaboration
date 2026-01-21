## InfluxDB 安装

InfluxDB 是一个高性能时序数据库，用于存储来自 reCamera 的检测坐标。

### 选项 A：Docker 部署（推荐）

点击上方的**部署**按钮，使用 Docker Compose 自动部署 InfluxDB。

部署完成后：
1. 访问 InfluxDB：http://localhost:8086
2. 默认凭据：admin / adminpassword
3. 组织：seeed
4. 存储桶：recamera

### 选项 B：手动安装

#### Windows

1. 从 [influxdata.com](https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-windows-amd64.zip) 下载 InfluxDB
2. 解压压缩包
3. 打开命令提示符并导航到解压目录
4. 运行：`influxd`

#### Linux

ARM 设备（如树莓派）：
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-linux-arm64.tar.gz
tar xvfz influxdb2-2.1.1-linux-arm64.tar.gz
cd influxdb2-2.1.1
./influxd
```

AMD64 设备：
```bash
wget https://dl.influxdata.com/influxdb/releases/influxdb2-2.1.1-linux-amd64.tar.gz
tar xvfz influxdb2-2.1.1-linux-amd64.tar.gz
cd influxdb2-2.1.1
./influxd
```

### 初始配置

1. 打开浏览器访问 `http://<您的IP>:8086`
2. 点击 **Get Started**
3. 填写您的信息：
   - 用户名：自选（请记住！）
   - 密码：自选（请记住！）
   - 组织：seeed（或您的偏好）
   - 存储桶名称：recamera
4. 点击 **Configure Later**
5. 进入 **Data** 验证您的存储桶
6. 进入 **API Tokens** 并复制您的令牌以备后用
