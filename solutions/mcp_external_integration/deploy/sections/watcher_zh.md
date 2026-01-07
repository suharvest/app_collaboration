# SenseCAP Watcher

AI 驱动的可穿戴语音助手，用于捕获语音指令并发送到云端处理。

## 设备配置

### 1. 开机配网

1. 长按电源键 3 秒开机
2. 扫描屏幕二维码连接 WiFi（需 2.4GHz 网络）

### 2. 绑定平台

1. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/home)
2. 点击 **Add Device**，扫描设备上的绑定二维码

### 3. 获取 MCP 端点（重要）

1. 进入 **Watcher Agent** → **Configuration**
2. 复制 **MCP Endpoint** 地址（`wss://...`）

> 下一步配置 MCP 桥接器时需要此地址

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| WiFi 连接失败 | 确保使用 2.4GHz 网络，非 5GHz |
| 无法绑定 | 尝试用手机热点排除办公网络限制 |
