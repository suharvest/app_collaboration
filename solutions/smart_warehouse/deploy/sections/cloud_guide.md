## SenseCraft Cloud Deployment

Use SenseCraft cloud platform for device management and MCP bridge connectivity.

### Architecture

| Component | Location | Description |
|-----------|----------|-------------|
| SenseCAP Watcher | On-site | Voice input device |
| SenseCraft Cloud | Cloud | Device management & MCP endpoint |
| Warehouse System | Local/Remote | Business logic & API |

### Prerequisites

- SenseCraft AI Platform account ([Register here](https://sensecraft.seeed.cc/ai/home))
- Docker installed on deployment device
- Stable internet connection

### Deployment Steps

1. **Deploy Warehouse System** - Start the warehouse Docker container
2. **Configure SenseCraft Platform** - Bind Watcher and get MCP endpoint
3. **Enable MCP Bridge** - Connect voice commands to warehouse API

> This is the recommended approach for most users. The cloud handles device connectivity and MCP routing automatically.
