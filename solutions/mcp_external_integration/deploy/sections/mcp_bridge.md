# MCP Bridge Service

Converts AI intents into warehouse system API calls. This is the key component connecting voice assistant to your business system.

## How It Works

```
Watcher → SenseCraft Cloud → MCP Endpoint → Bridge → Warehouse API
```

## Configuration

You'll need to provide:

| Field | Description | Source |
|-------|-------------|--------|
| MCP Endpoint | WebSocket address | SenseCraft AI → Watcher Agent → Configuration |
| API Key | Warehouse system access key | Warehouse → User Management → API Key |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Verify MCP endpoint address is correct |
| Network blocked | Try mobile hotspot to bypass corporate firewall |
| 401 Unauthorized | Check if API key is correct |
