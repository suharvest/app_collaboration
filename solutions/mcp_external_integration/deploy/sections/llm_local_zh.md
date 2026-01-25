# 本地 LLM 与 TTS 部署

在 reComputer J4012（Jetson Orin NX 16GB）上部署 Qwen3-8B 大语言模型和 TTS 语音合成服务，实现完全本地化的 AI 推理。

## 服务组件

| 服务 | 端口 | 用途 |
|------|------|------|
| Ollama (Qwen3-8B) | 11434 | LLM 推理，提供 OpenAI 兼容 API |

## 硬件要求

- reComputer J4012（Jetson Orin NX 16GB）
- 已安装 JetPack 6.x
- 已配置 NVIDIA 容器运行时
- 至少 15GB 可用磁盘空间
- 与 R1100 网络互通

## 模型信息

| 项目 | 规格 |
|------|------|
| 模型 | Qwen3-8B（4-bit 量化） |
| 显存 | ~5GB 模型 + 1-2GB KV 缓存 |
| 速度 | 生成速度 ~13 tokens/秒 |
| 变体 | `qwen3:8b`（推理）/ `qwen3:8b-chat`（对话） |

## 部署完成后

1. LLM API 地址为 `http://<j4012-ip>:11434/v1/chat/completions`
2. 更新小智服务配置，将 LLM/TTS 指向 J4012 的 IP 地址
3. 首次启动需下载模型（~5GB），后续启动很快
4. 语音对话场景使用 `qwen3:8b-chat` 变体（无推理 token）
