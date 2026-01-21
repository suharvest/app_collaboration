## 部署概述

本方案部署一套完整的边缘语音 AI 系统，专为零售环境设计。部署包含三个主要步骤：

1. **刷写 OpenWrt 固件** - 将优化的 OpenWrt 固件安装到 reRouter
2. **配置 reSpeaker** - 在电脑上设置 XVF3800 麦克风阵列
3. **部署语音服务** - 自动将 Docker 容器部署到 reRouter

## 前置条件

开始前，请确保您拥有：

- reRouter CM4（至少 4GB 内存和 32GB 存储）
- reSpeaker XVF3800 4 麦克风阵列
- USB-C 数据线（用于 reSpeaker 配置）
- 网线（用于 reRouter 连接）
- 运行 Linux、macOS 或 Windows 的电脑（用于 reSpeaker 配置）

## 网络配置

部署完成后，可访问以下界面：

| 界面 | 地址 | 说明 |
|------|------|------|
| OpenWrt 管理 | http://192.168.49.1 | 路由器配置 |
| 语音客户端 | http://192.168.49.1:8090 | 实时 ASR 和设备设置 |
