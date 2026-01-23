## Edge Computing Deployment

All processing happens on the local edge device - ideal for air-gapped environments.

### Architecture

| Component | Location | Description |
|-----------|----------|-------------|
| SenseCAP Watcher | On-site | Voice input device |
| reComputer J4012 | On-site | Runs all services locally |
| Warehouse System | On-site | Business logic & API on edge |

### Prerequisites

- reComputer J4012 or equivalent edge device
- Docker installed on edge device
- Local WiFi network for Watcher connectivity

### Deployment Steps

1. **Deploy All Services to Edge** - Deploy warehouse + MCP bridge to reComputer
2. **Configure Local Network** - Set up local WiFi for Watcher
3. **Pair Watcher** - Connect Watcher to edge device's MCP endpoint

### Advantages

- Works without internet connection
- Lowest latency for voice commands
- Complete data isolation
- Suitable for secure or remote facilities

### Considerations

- Requires more powerful edge hardware
- Updates must be applied manually
- Limited to local network coverage
