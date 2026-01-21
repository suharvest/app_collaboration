## 部署概述

本解决方案部署一个实时热力图系统，包含四个主要组件：

1. **InfluxDB** - 用于存储检测坐标的时序数据库
2. **reCamera** - 运行 Node-RED 人员检测的边缘 AI 设备
3. **Grafana** - 用于可视化和分析的仪表板
4. **热力图页面** - 基于 HTML5 Canvas 的热力可视化

## 先决条件

- reCamera 设备（2002 系列、云台版或 HQ POE 版）
- 运行 Windows、macOS 或 Linux 的电脑
- 已安装 Docker（用于本地部署 InfluxDB/Grafana）
- reCamera 与电脑之间的网络连接

## 网络要求

确保 reCamera 和您的电脑在**同一网络**中。这对于以下功能是必需的：
- reCamera 向 InfluxDB 发送数据
- Grafana 显示来自 reCamera 的实时视频流
- 热力图页面从 InfluxDB 查询数据

## 部署完成后

完成所有步骤后，您可以访问：
- **Grafana 仪表板**: http://localhost:3000
- **热力图页面**: http://localhost:8080/index.html
- **InfluxDB 界面**: http://localhost:8086
