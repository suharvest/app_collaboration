# Voice AI Service Remote Deployment

Deploy the Voice AI service to reComputer R1100 (Warehouse Box) via SSH.

## Deployment Architecture

```
+-------------+     +-----------------------------------+
|   Watcher   |---->|      reComputer R1100             |
| Voice Input |     |  +---------------------------+    |
+-------------+     |  |   xiaozhi-server          |    |
                    |  |   - VAD (Silero)          |    |
                    |  |   - ASR (SherpaASR)       |    |
                    |  |   - LLM (Cloud/Jetson)    |    |
                    |  |   - TTS (Edge/Kokoro)     |    |
                    |  +---------------------------+    |
                    |  +---------------------------+    |
                    |  |   mcp-endpoint            |    |
                    |  |   Connect to Warehouse API |    |
                    |  +---------------------------+    |
                    +-----------------------------------+
```

## Connection Info

- Default SSH port: 22
- Default username: root (OpenWrt) or your configured username

## Notes

1. Ensure R1100 is connected to the network
2. First deployment requires pulling Docker images (~800MB)
3. Edge Computing mode requires Jetson LLM/TTS services deployed first
