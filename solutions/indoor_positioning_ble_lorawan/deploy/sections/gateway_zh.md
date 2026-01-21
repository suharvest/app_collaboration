## LoRaWAN 网关设置

LoRaWAN 网关接收追踪器的数据并将其转发到您的网络服务器。

### SenseCAP M2 网关设置

1. **开机** - 使用随附的适配器将网关连接电源
2. **连接网络** - 使用以太网电缆或通过 SenseCraft App 配置 WiFi
3. **等待初始化** - 准备就绪后 LED 将变为常亮绿色

### 网络服务器选项

选择以下选项之一来接收追踪器数据：

**选项 A：SenseCraft Data 平台（推荐初学者）**
1. 下载 SenseCraft App
2. 扫描网关上的二维码
3. 按照设置向导绑定网关
4. 您的网关将自动连接到 SenseCraft Data

**选项 B：ChirpStack（自托管）**
1. 设置 ChirpStack 服务器实例
2. 通过 IP 地址访问网关 Web 界面
3. 配置网络服务器设置以指向您的 ChirpStack
4. 使用网关 EUI 在 ChirpStack 中添加网关

### 验证网关状态

- **SenseCraft Data**：在应用程序或 Web 门户中检查网关状态
- **ChirpStack**：导航到 Gateways 并验证"Last seen"时间戳

### 覆盖提示

- 将网关放置在中心位置，较高处
- 避免放置在金属外壳或厚墙附近
- 一个网关通常覆盖室内 2km 半径
