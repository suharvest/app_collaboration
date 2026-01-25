# Xiaozhi Voice Server Deployment

Deploy the Xiaozhi voice AI server and MCP endpoint on the reComputer R1100 (warehouse box).

## Services

| Service | Port | Purpose |
|---------|------|---------|
| xiaozhi-server | 18000 (WS), 18003 (HTTP) | Voice AI processing (VAD, ASR, LLM, TTS) |
| mcp-endpoint | 18004 | MCP tool endpoint for warehouse API integration |

## Requirements

- Docker installed and running
- At least 3GB free disk space
- Ports 18000, 18003, 18004 available
- Network access to LLM/TTS service (external API or J4012)

## After Deployment

1. Xiaozhi server WebSocket available at `ws://<host>:18000/xiaozhi/v1/`
2. Configure Watcher firmware to connect to this WebSocket address
3. In warehouse system, go to **MCP Management** to connect the MCP endpoint
4. The MCP endpoint enables voice commands to call warehouse APIs
