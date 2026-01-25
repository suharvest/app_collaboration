# Voice AI Service Local Deployment

Deploy the Xiaozhi Voice AI service locally for processing warehouse management voice commands.

## Service Components

| Service | Port | Purpose |
|---------|------|---------|
| xiaozhi-server | 18000 (WS), 18003 (HTTP) | Voice processing (VAD, ASR, LLM, TTS) |
| mcp-endpoint | 18004 | MCP tool endpoint |

## Deployment Options

### Private Cloud Mode
- VAD/ASR: Local processing (SherpaASR)
- LLM: Cloud API you provide (DeepSeek, OpenAI, etc.)
- TTS: Edge TTS (free Microsoft speech synthesis)

### Edge Computing Mode
- VAD/ASR: Local processing (SherpaASR)
- LLM: Connect to MLC LLM on Jetson (Qwen3-8B)
- TTS: Connect to Kokoro TTS on Jetson (streaming)

## Prerequisites

- Docker installed and running
- At least 3GB available disk space
- Private Cloud mode requires internet connection
- Edge Computing mode requires Jetson device with LLM/TTS deployed

## Latency Comparison

| Mode | ASR | LLM TTFT | TTS First Frame | Total Latency |
|------|-----|----------|-----------------|---------------|
| Private Cloud | ~150ms | ~200-400ms | ~200ms | **~0.8-1.2s** |
| Edge Computing | ~150ms | ~300-500ms | ~300ms | **~1.0-1.5s** |
