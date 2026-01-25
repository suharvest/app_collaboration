# 小智语音服务部署

在 reComputer R1100（仓管盒子）上部署小智语音 AI 服务和 MCP 端点。

## 服务组件

| 服务 | 端口 | 用途 |
|------|------|------|
| xiaozhi-server | 18000 (WS), 18003 (HTTP) | 语音 AI 处理（VAD、ASR、LLM、TTS） |
| mcp-endpoint | 18004 | MCP 工具端点，对接仓库 API |

## 前提条件

- Docker 已安装并运行
- 至少 3GB 可用磁盘空间
- 端口 18000、18003、18004 可用
- 能够访问 LLM/TTS 服务（外部 API 或 J4012）

## 部署完成后

1. 小智服务 WebSocket 地址为 `ws://<host>:18000/xiaozhi/v1/`
2. 配置 Watcher 固件连接到此 WebSocket 地址
3. 在仓库管理系统中，进入 **MCP 管理** 连接 MCP 端点
4. MCP 端点使语音指令能够调用仓库管理 API
