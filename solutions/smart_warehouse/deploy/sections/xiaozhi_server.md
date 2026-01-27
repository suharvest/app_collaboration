# Control Panel Configuration

After deploying the voice service, configure model APIs and get the MCP endpoint address from the control panel.

## Step 1: Login to Control Panel

1. Open browser and visit `http://server-ip:8002`
2. First visit requires registration - **first registered account becomes admin**
3. Login with your registered account

## Step 2: Configure Model APIs

After login, go to "Model Configuration" menu:

| Setting | Description | Recommended |
|---------|-------------|-------------|
| LLM | Select provider and enter API key | Zhipu AI (free quota) or Alibaba Qwen |
| TTS | Select TTS service | Huoshan Stream TTS or Lingxi TTS |
| ASR | Uses local FunASR by default | No configuration needed |

> For first-time users, "Zhipu AI" is recommended as it offers free quota

## Step 3: Get MCP Endpoint

1. Go to "Parameters" menu
2. Find `mcp_endpoint` parameter
3. Copy MCP WebSocket address (format: `ws://IP:8004/mcp_endpoint/mcp/?token=xxx`)
4. This address will be entered in warehouse system in next step

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot access control panel | Check if port 8002 is open |
| Model call fails | Verify API key is correct and account has balance |
| MCP endpoint connection fails | Check if firewall allows port 8004 |
