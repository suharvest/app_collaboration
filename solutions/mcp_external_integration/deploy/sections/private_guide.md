## Private Cloud Deployment

Self-hosted deployment for organizations requiring data privacy and full control.

### Architecture

| Component | Location | Description |
|-----------|----------|-------------|
| SenseCAP Watcher | On-site | Voice input device |
| MCP Bridge | Local network | Self-hosted MCP endpoint |
| Warehouse System | Local network | Business logic & API |

### Prerequisites

- Docker installed on deployment device
- Local network connectivity between all devices
- No external internet dependency after setup

### Deployment Steps

1. **Deploy Warehouse System** - Start the warehouse Docker container on your server
2. **Deploy MCP Bridge** - Run MCP bridge service locally (no cloud dependency)
3. **Configure Watcher** - Point Watcher to local MCP endpoint

### Key Differences from Cloud

- All data stays within your local network
- No SenseCraft cloud account required
- MCP bridge runs as a local Docker service
- Higher latency for initial setup, but lower runtime latency
