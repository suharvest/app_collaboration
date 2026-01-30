Use SenseCAP Watcher and MCP bridge to enable voice commands that directly call your warehouse system APIs.

## Deployment Flow

Choose your deployment mode and follow the steps:

### Cloud Mode ⭐Recommended
```
1. Deploy Warehouse System → Get API key
2. Deploy Voice Service → Configure SenseCraft cloud
3. Configure SenseCraft Platform → Get device connection URL
4. Enable MCP Bridge → Connect voice and warehouse system
5. Test → Try voice commands
```

### Private Cloud Mode
```
1. Deploy Warehouse System → Get API key
2. Deploy Voice Service → Configure your cloud AI APIs
3. Configure Control Panel → Get MCP endpoint
4. Enable MCP Bridge → Connect voice and warehouse system
5. Test → Try voice commands
```

### Edge Computing Mode
```
1. Deploy Warehouse System → Get API key
2. Deploy AGX Orin AI → Provide local LLM/TTS
3. Deploy Voice Service → Connect to AGX Orin
4. Configure Control Panel → Get MCP endpoint
5. Enable MCP Bridge → Connect voice and warehouse system
6. Test → Try voice commands
```

## Prerequisites

| Type | Requirement |
|------|-------------|
| Hardware | SenseCAP Watcher, reComputer R1100 (or PC with Docker) |
| Hardware (Edge) | NVIDIA AGX Orin for local AI processing |
| Software | Docker installed and running |
| Account | [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/home) account |

## Deployment Options

| Mode | AI Service | Network | Response Time |
|------|------------|---------|---------------|
| Cloud | SenseCraft Cloud | Internet required | ~0.5-0.8s |
| Private Cloud | Your cloud APIs | Internet required | ~0.8-1.2s |
| Edge Computing | Local AGX Orin | LAN only | ~1.0-1.5s |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Service won't start | Check if ports are in use by other programs |
| Watcher won't connect to WiFi | Ensure it's 2.4GHz network, not 5GHz |
| No voice response | Check all service status |
| AGX Orin connection failed | Verify IP address and network connectivity |

> Need help? Visit [Wiki Documentation](https://wiki.seeedstudio.com/cn/mcp_external_system_integration/).
