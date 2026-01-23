# 远程部署

将 InfluxDB 和 Grafana 部署到远程设备（reComputer、树莓派等）。

## 开始之前

1. **将目标设备连接到网络**
   - 确保设备与您的电脑在同一网络
   - 记录设备的 IP 地址

2. **获取设备凭据**
   - SSH 用户名（通常是 `root`、`pi` 或 `recomputer`）
   - SSH 密码

## 连接设置

填写以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 设备 IP | 目标设备 IP 地址 | 192.168.1.100 |
| SSH 用户名 | 登录用户名 | root |
| SSH 密码 | 登录密码 | your-password |
| SSH 端口 | SSH 端口（默认 22） | 22 |

## 部署完成后

访问 InfluxDB：`http://<设备IP>:8086`
- 账号：admin / adminpassword
- 组织：seeed，存储桶：recamera

进入 **API Tokens** 复制令牌，后续配置需要。

访问 Grafana：`http://<设备IP>:3000`
- 默认账号：admin / admin
