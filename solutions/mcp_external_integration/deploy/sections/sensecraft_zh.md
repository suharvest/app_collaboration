# SenseCraft 平台配置

配置 SenseCAP Watcher 并获取设备连接地址，用于打通语音和仓管系统。

## 第一步：开机配网

1. 长按电源键 3 秒开机
2. 扫描屏幕二维码连接 WiFi（必须是 2.4GHz 网络）

## 第二步：绑定平台

1. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/home)
2. 点击 **Add Device**，扫描 Watcher 上的绑定二维码

## 第三步：获取设备连接地址

1. 进入 **Watcher Agent** -> **Configuration**
2. 复制 **MCP Endpoint** 地址（以 `wss://` 开头）

> 请保存好这个地址，下一步启用连接桥接时需要用到

## 故障排除

| 问题 | 解决方案 |
|------|---------|
| WiFi 连接失败 | 确保使用 2.4GHz 网络，不是 5GHz |
| 无法绑定设备 | 尝试用手机热点，排除办公网络限制 |
| 找不到设备连接地址 | 确保 Watcher 固件是最新版本 |
