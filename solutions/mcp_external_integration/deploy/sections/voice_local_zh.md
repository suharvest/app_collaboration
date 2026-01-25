# 语音 AI 服务本机部署

在本机部署小智语音 AI 服务，用于处理仓库管理语音指令。

## 服务组件

| 服务 | 端口 | 用途 |
|------|------|------|
| xiaozhi-server | 18000 (WS), 18003 (HTTP) | 语音处理（VAD、ASR、LLM、TTS） |
| mcp-endpoint | 18004 | MCP 工具端点 |

## 方案说明

### 私有云方案
- VAD/ASR：本地运行（SherpaASR）
- LLM：使用您填写的云端 API（DeepSeek、OpenAI 等）
- TTS：使用 Edge TTS（微软免费语音合成）

### 边缘计算方案
- VAD/ASR：本地运行（SherpaASR）
- LLM：连接 Jetson 上的 MLC LLM（Qwen3-8B）
- TTS：连接 Jetson 上的 Kokoro TTS（流式）

## 前提条件

- Docker 已安装并运行
- 至少 3GB 可用磁盘空间
- 私有云方案需要互联网连接
- 边缘计算方案需要 Jetson 设备已部署 LLM/TTS

## 延迟对比

| 方案 | ASR | LLM TTFT | TTS 首帧 | 总延迟 |
|------|-----|----------|----------|--------|
| 私有云 | ~150ms | ~200-400ms | ~200ms | **~0.8-1.2s** |
| 边缘计算 | ~150ms | ~300-500ms | ~300ms | **~1.0-1.5s** |
