## Preset: SenseCraft Cloud {#sensecraft_cloud}

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

### Target: Local Deployment {#warehouse_local config=devices/recomputer.yaml default=true}

![Wiring](intro/gallery/api-endpoint.png)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target: Remote Deployment {#warehouse_remote config=devices/warehouse_remote.yaml}

![Wiring](intro/gallery/api-endpoint.png)

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

---

## Step 2: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_server.yaml}

### Target: Local Deployment {#voice_service_local config=devices/xiaozhi_server.yaml}

### Target: Remote Deployment (R1100) {#voice_service_remote config=devices/xiaozhi_remote.yaml default=true}

---

## Step 3: SenseCraft Platform {#sensecraft type=manual required=true}

### Wiring

![Wiring](intro/gallery/mcp-connected.png)

1. Power on the SenseCAP Watcher
2. Connect Watcher to WiFi via QR code
3. Login to SenseCraft AI platform and bind device
4. Get MCP Endpoint from Watcher Agent settings

---

## Step 4: MCP Bridge Service {#mcp_bridge type=script required=true config=devices/mcp_bridge.yaml}

### Wiring

![Wiring](intro/gallery/mcp-endpoint.png)

1. Get MCP endpoint from SenseCraft AI platform
2. Create API key in warehouse system
3. Configure and start MCP bridge

---

## Step 5: Demo & Testing {#demo type=manual required=false}

### Wiring

![Wiring](intro/gallery/xiaozhi-stock-in.png)

1. Speak to Watcher to query inventory
2. Try stock-in and stock-out commands
3. Check results in warehouse web interface

---

## Preset: Private Cloud {#private_cloud}

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

### Target: Local Deployment {#warehouse_local config=devices/recomputer.yaml default=true}

![Wiring](intro/gallery/api-endpoint.png)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target: Remote Deployment {#warehouse_remote config=devices/warehouse_remote.yaml}

![Wiring](intro/gallery/api-endpoint.png)

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

---

## Step 2: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_server.yaml}

### Target: Local Deployment {#voice_service_local config=devices/xiaozhi_server.yaml}

### Target: Remote Deployment (R1100) {#voice_service_remote config=devices/xiaozhi_remote.yaml default=true}

---

## Step 3: Xiaozhi Control Panel {#xiaozhi_console type=manual required=true}

### Wiring

![Wiring](intro/gallery/api-endpoint.png)

1. Access control panel at http://server-ip:8002
2. Register admin account (first user is admin)
3. Configure LLM/TTS API keys in Model Configuration
4. Copy MCP Endpoint address from Parameters

---

## Step 4: MCP Bridge Service {#mcp_bridge type=script required=true config=devices/mcp_bridge.yaml}

### Wiring

![Wiring](intro/gallery/mcp-endpoint.png)

1. Get MCP endpoint from SenseCraft AI platform
2. Create API key in warehouse system
3. Configure and start MCP bridge

---

## Step 5: Demo & Testing {#demo type=manual required=false}

### Wiring

![Wiring](intro/gallery/xiaozhi-stock-in.png)

1. Speak to Watcher to query inventory
2. Try stock-in and stock-out commands
3. Check results in warehouse web interface

---

## Preset: Edge Computing {#edge_computing}

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/recomputer.yaml}

### Target: Local Deployment {#warehouse_local config=devices/recomputer.yaml default=true}

![Wiring](intro/gallery/api-endpoint.png)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target: Remote Deployment {#warehouse_remote config=devices/warehouse_remote.yaml}

![Wiring](intro/gallery/api-endpoint.png)

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

---

## Step 2: AGX Orin LLM & TTS {#agx_orin_llm_tts type=docker_deploy required=true config=devices/llm_agx_orin.yaml}

---

## Step 3: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_server.yaml}

### Target: Local Deployment {#voice_service_local config=devices/xiaozhi_server.yaml}

### Target: Remote Deployment (R1100) {#voice_service_remote config=devices/xiaozhi_remote.yaml default=true}

---

## Step 4: Xiaozhi Control Panel {#xiaozhi_console type=manual required=true}

### Wiring

![Wiring](intro/gallery/api-endpoint.png)

1. Access control panel at http://server-ip:8002
2. Register admin account (first user is admin)
3. Configure LLM/TTS API keys in Model Configuration
4. Copy MCP Endpoint address from Parameters

---

## Step 5: MCP Bridge Service {#mcp_bridge type=script required=true config=devices/mcp_bridge.yaml}

### Wiring

![Wiring](intro/gallery/mcp-endpoint.png)

1. Get MCP endpoint from SenseCraft AI platform
2. Create API key in warehouse system
3. Configure and start MCP bridge

---

## Step 6: Demo & Testing {#demo type=manual required=false}

### Wiring

![Wiring](intro/gallery/xiaozhi-stock-in.png)

1. Speak to Watcher to query inventory
2. Try stock-in and stock-out commands
3. Check results in warehouse web interface

---

# Deployment Complete

Congratulations! Your Smart Warehouse Management system is now deployed and ready to use.

## Next Steps

- [Access Warehouse System](http://localhost:2125)
- [View Documentation](https://wiki.seeedstudio.com/cn/mcp_external_system_integration/)
- [Report Issues on GitHub](https://github.com/suharvest/warehouse_system/issues)
