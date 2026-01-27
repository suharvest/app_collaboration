## SenseCraft 云方案部署

使用 SenseCraft 云平台进行设备管理和 MCP 桥接连接。

### 架构说明

| 组件 | 位置 | 说明 |
|------|------|------|
| SenseCAP Watcher | 现场 | 语音输入设备 |
| SenseCraft 云平台 | 云端 | 设备管理与 MCP 端点 |
| 仓库管理系统 | 本地/远程 | 业务逻辑与 API |

### 前提条件

- SenseCraft AI 平台账户（[点击注册](https://sensecraft.seeed.cc/ai/home)）
- 部署设备已安装 Docker
- 稳定的互联网连接

### 部署步骤

1. **部署仓库系统** - 启动仓库 Docker 容器
2. **配置 SenseCraft 平台** - 绑定 Watcher 并获取 MCP 端点
3. **启用 MCP 桥接** - 连接语音指令与仓库 API

> 这是大多数用户推荐的方案。云平台自动处理设备连接和 MCP 路由。
