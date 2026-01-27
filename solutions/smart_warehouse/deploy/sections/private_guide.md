## Private Cloud Deployment

Deploy xiaozhi-esp32-server locally, use cloud vendor APIs for TTS/LLM, manage devices via the control panel.

### Architecture

| Component | Location | Description |
|-----------|----------|-------------|
| SenseCAP Watcher | On-site | Voice input device |
| reComputer R1100 | Local | Runs xiaozhi backend + warehouse system |
| Cloud Vendor API | Cloud | TTS/LLM services (Zhipu, Alibaba, etc.) |

### Prerequisites

- reComputer R1100 or equivalent (4GB+ RAM)
- Docker installed
- Internet connection (for cloud API calls)

### Deployment Steps

1. **Deploy Xiaozhi Backend** - Deploy xiaozhi-esp32-server on R1100
2. **Deploy Warehouse System** - Start warehouse Docker container
3. **Configure Models** - Login to control panel, configure cloud TTS/LLM API keys
4. **Get MCP Endpoint** - Copy MCP WebSocket address from control panel
5. **Configure Warehouse** - Enter MCP endpoint in warehouse "Agent Configuration"

### Control Panel Configuration

Control Panel URL: `http://R1100-IP:8002`

| Setting | Description |
|---------|-------------|
| Model Config → LLM | Enter Zhipu/Alibaba API keys |
| Model Config → TTS | Configure TTS service keys |
| Parameters → MCP Endpoint | Copy WebSocket address for warehouse system |

### Comparison with Other Options

| Aspect | Cloud | Private Cloud | Edge Computing |
|--------|-------|---------------|----------------|
| Voice Backend | SenseCraft AI | xiaozhi-esp32-server | xiaozhi-esp32-server |
| TTS/LLM | SenseCraft Cloud | Cloud Vendor API | Local AI inference |
| Management | SenseCraft Platform | Control Panel | Control Panel |
| Network | Internet required | Internet required | LAN only |

> Xiaozhi backend deployment: [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)
