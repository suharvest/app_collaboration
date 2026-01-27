## 私有云方案部署

在本地部署 xiaozhi-esp32-server，使用云厂商 API 提供 TTS/LLM 能力，通过智控台管理设备。

### 架构说明

| 组件 | 位置 | 说明 |
|------|------|------|
| SenseCAP Watcher | 现场 | 语音输入设备 |
| reComputer R1100 | 本地 | 运行小智后端 + 仓管系统 |
| 云厂商 API | 云端 | 提供 TTS/LLM 服务（智谱、阿里百炼等） |

### 前提条件

- reComputer R1100 或同等设备（4GB+ 内存）
- Docker 已安装
- 互联网连接（调用云厂商 API）

### 部署步骤

1. **部署小智后端** - 在 R1100 上部署 xiaozhi-esp32-server
2. **部署仓管系统** - 启动仓库 Docker 容器
3. **智控台配置模型** - 登录智控台，配置云厂商 TTS/LLM API 密钥
4. **获取 MCP 端点** - 从智控台复制 MCP WebSocket 地址
5. **仓管系统配置** - 在仓管系统「智能体配置」中填入 MCP 端点

### 智控台配置

智控台地址：`http://R1100的IP:8002`

| 配置项 | 说明 |
|--------|------|
| 模型配置 → 大语言模型 | 填入智谱/阿里百炼等 API 密钥 |
| 模型配置 → 语音合成 | 配置 TTS 服务密钥 |
| 参数管理 → MCP 端点 | 复制 WebSocket 地址给仓管系统 |

### 与其他方案对比

| 对比项 | 云方案 | 私有云方案 | 边缘计算方案 |
|--------|--------|-----------|-------------|
| 语音后端 | SenseCraft AI | xiaozhi-esp32-server | xiaozhi-esp32-server |
| TTS/LLM | SenseCraft 云端 | 云厂商 API | AI 盒子本地推理 |
| 管理平台 | SenseCraft 平台 | 智控台 | 智控台 |
| 网络依赖 | 需要互联网 | 需要互联网 | 仅需局域网 |

> 小智后端部署：[xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
