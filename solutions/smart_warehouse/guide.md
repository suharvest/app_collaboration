## Preset: SenseCraft Cloud {#sensecraft_cloud}

Use [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud service for voice AI. Simplest setup - just deploy the warehouse system and connect your Watcher to SenseCraft platform.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R1100 | Runs warehouse management system |

**What you'll get:**
- Voice-controlled inventory management (stock in/out by speaking)
- Real-time inventory dashboard
- Works with SenseCAP Watcher out of the box

**Requirements:** Internet connection · [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free)

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target: Local Deployment {#warehouse_local type=local config=devices/recomputer.yaml}

Run the warehouse system on this computer.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target: Remote Deployment (R1100) {#warehouse_remote type=remote config=devices/warehouse_remote.yaml default=true}

Deploy to reComputer R1100 edge device.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect R1100 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address reComputer-R110x.local (or check your router)
3. Enter username recomputer, password 12345678
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](assets/inventory_import.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Configure Watcher Device {#sensecraft type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher, connect your phone to the WiFi hotspot displayed on the device screen, configure WiFi in the popup page, device will restart and show a 6-digit verification code
2. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/), click "Watcher Agent" → "Bind Device", enter the 6-digit code shown on your Watcher
3. Click "Create" to make a new Agent, set name and language, then save
4. Click the settings icon on your Agent card, go to "MCP Setting" and copy the endpoint URL

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh page |

---

## Step 4: Connect to Agent {#mcp_bridge type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

This step enables Watcher to control the warehouse system:

1. Open warehouse system, go to "Agent Configuration" on the left sidebar
2. Click "Add Agent", fill in the name, paste the endpoint URL from previous step
3. Click "Save and Start"
4. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 5: Demo & Testing {#demo type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure MCP bridge service is running |
| Inventory not updated | Refresh the web page to see latest data |

### Deployment Complete

Your voice-controlled warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- SenseCraft Platform: [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

Try saying "Stock in 10 boxes of apples" to test voice inventory management.

---

## Preset: Private Cloud {#private_cloud}

Self-host the voice AI server while using cloud APIs (DeepSeek, OpenAI, etc.) for LLM and TTS. Your data stays on your network - only API calls go to the cloud.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R1100 | Runs warehouse system + voice AI server |

**What you'll get:**
- Full control over your data - inventory stays on your network
- Flexible AI model choices (DeepSeek, GPT-4, Qwen, etc.)
- Customize voice assistant prompts and behavior

**Requirements:** Internet connection (for LLM/TTS API) · API keys for your AI provider (recommend [DeepSeek](https://platform.deepseek.com/) - free credits on signup)

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target: Local Deployment {#warehouse_local type=local config=devices/recomputer.yaml}

1. Ensure Docker is installed and running on your machine
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target: Remote Deployment (R1100) {#warehouse_remote type=remote config=devices/warehouse_remote.yaml default=true}

![Wiring](gallery/R1100_connected.png)

1. Connect R1100 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address reComputer-R110x.local (or check your router)
3. Enter username recomputer, password 12345678
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](assets/inventory_import.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_server.yaml}

Deploy the voice AI service to enable voice interaction with Watcher. Select "Private Cloud" mode and fill in your LLM API details.

### Target: Local Deployment {#voice_local type=local config=devices/xiaozhi_server.yaml}

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target: Remote Deployment (R1100) {#voice_remote type=remote config=devices/xiaozhi_remote.yaml default=true}

1. Enter R1100 IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### LLM API Configuration

Fill in the following during deployment:

| Field | Example | Description |
|-------|---------|-------------|
| API URL | `https://api.deepseek.com/v1` | OpenAI-compatible API endpoint |
| Model Name | `deepseek-chat` | Model to use |
| API Key | `sk-...` | Get from your provider |

TTS uses free Edge TTS by default, no additional configuration needed.

### Getting API Keys

- **DeepSeek** (Recommended): Visit [platform.deepseek.com](https://platform.deepseek.com/), free credits for new users
- **OpenAI**: Visit [platform.openai.com](https://platform.openai.com/)
- **Moonshot**: Visit [platform.moonshot.cn](https://platform.moonshot.cn/)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Image pull failed | Check network connection, or configure Docker mirror |
| Port in use | Check if ports 18000, 18003, 18004 are used by other services |
| API call failed | Verify API key is correct and has sufficient balance |

---

## Step 4: Configure Watcher Device {#watcher_config type=manual required=true}

Connect your Watcher to the local voice service:

1. Power on Watcher, connect your phone to the WiFi hotspot displayed on the device screen
2. In the popup page, tap the "Advanced" tab
3. Change OTA URL to: `http://server-ip:18003` (server IP is the device running voice service)
4. Configure WiFi (2.4GHz only), device will restart and show a 6-digit verification code
5. Visit voice service console at `http://server-ip:18003` and bind the device code

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Binding failed | Verify OTA URL is correct and voice service is running |

---

## Step 5: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open warehouse system, go to "Agent Configuration" on the left sidebar
2. Click "Add Agent", fill in name, enter `ws://server-ip:18004/mcp` in Endpoint field
3. Click "Save and Start"
4. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is correct, voice service is running |
| Status stays Disconnected | Confirm MCP endpoint service (port 18004) is running |

---

## Step 6: Demo & Testing {#demo type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

### Deployment Complete

Your private cloud warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Voice Service Console: http://\<server-ip\>:18003

Your data stays on your network. Try saying "How many apples left?" to test.

---

## Preset: Edge Computing {#edge_computing}

Run everything locally including LLM and TTS - no internet required. Ideal for air-gapped environments or strict data compliance.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R1100 | Runs warehouse system + voice AI server |
| reComputer J4012 | Runs local LLM (Qwen3-8B) and TTS |

**What you'll get:**
- 100% offline operation - works without internet
- All data stays within your local network
- Local LLM inference at ~16 tokens/sec

**Requirements:** reComputer J4012 or equivalent Jetson device · Internet needed for initial deployment only

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target: Local Deployment {#warehouse_local type=local config=devices/recomputer.yaml}

1. Ensure Docker is installed and running on your machine
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target: Remote Deployment (R1100) {#warehouse_remote type=remote config=devices/warehouse_remote.yaml default=true}

![Wiring](gallery/R1100_connected.png)

1. Connect R1100 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address reComputer-R110x.local (or check your router)
3. Enter username recomputer, password 12345678
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](assets/inventory_import.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Jetson Local AI {#jetson_ai type=docker_deploy required=true config=devices/llm_jetson.yaml}

Deploy local LLM and TTS services on the Jetson device:

1. Connect Jetson (e.g., reComputer J4012) to power and ethernet
2. Enter Jetson IP address and SSH credentials
3. Select model (Qwen3-8B recommended, requires ~4.3GB VRAM)
4. Choose deployment method:
   - **Offline Package**: Use pre-downloaded images and models (recommended)
   - **Online Download**: Download from registry (requires internet)
5. Click Deploy and wait for image import and service startup

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Confirm Jetson is powered on, verify IP address |
| Insufficient VRAM | Choose smaller model (Qwen3-4B ~2.5GB, Qwen3-1.7B ~1.2GB) |
| Deployment takes long | Offline package is large (~5GB), please be patient |

---

## Step 4: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_remote.yaml}

Deploy voice AI service on R1100, connecting to Jetson for inference. Select "Edge Computing" mode and enter the Jetson IP address.

### Target: Local Deployment {#voice_local type=local config=devices/xiaozhi_server.yaml}

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target: Remote Deployment (R1100) {#voice_remote type=remote config=devices/xiaozhi_remote.yaml default=true}

1. Enter R1100 IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Configuration Notes

Enter the Jetson IP address during deployment (auto-filled if Jetson was deployed in previous step). The voice service will connect to the LLM and TTS running on Jetson for local inference.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to Jetson | Check if R1100 and Jetson are on the same network |
| Response is slow | Confirm Jetson service is running, visit `http://Jetson-IP:8000/health` to check |

---

## Step 5: Configure Watcher Device {#watcher_config type=manual required=true}

Connect your Watcher to the local voice service:

1. Power on Watcher, connect your phone to the WiFi hotspot displayed on the device screen
2. In the popup page, tap the "Advanced" tab
3. Change OTA URL to: `http://server-ip:18003` (server IP is the device running voice service)
4. Configure WiFi (2.4GHz only), device will restart and show a 6-digit verification code
5. Visit voice service console at `http://server-ip:18003` and bind the device code

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Binding failed | Verify OTA URL is correct and voice service is running |

---

## Step 6: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open warehouse system, go to "Agent Configuration" on the left sidebar
2. Click "Add Agent", fill in name, enter `ws://server-ip:18004/mcp` in Endpoint field
3. Click "Save and Start"
4. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is correct, voice service is running |
| Status stays Disconnected | Confirm MCP endpoint service (port 18004) is running |

---

## Step 7: Demo & Testing {#demo type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

### Deployment Complete

Your fully offline warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Voice Service Console: http://\<server-ip\>:18003
- LLM Health Check: http://\<jetson-ip\>:8000/health

100% offline operation - no internet required after deployment.
