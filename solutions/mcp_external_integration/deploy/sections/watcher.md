# SenseCAP Watcher

AI-powered wearable voice assistant that captures voice commands and sends them to the cloud for processing.

## Device Setup

### 1. Power On & Connect WiFi

1. Long press power button for 3 seconds
2. Scan the QR code on screen to connect WiFi (2.4GHz only)

### 2. Bind to Platform

1. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/home)
2. Click **Add Device**, scan the binding QR code on device

### 3. Get MCP Endpoint (Important)

1. Go to **Watcher Agent** → **Configuration**
2. Copy the **MCP Endpoint** address (`wss://...`)

> You'll need this address for MCP bridge configuration

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WiFi connection failed | Make sure to use 2.4GHz network, not 5GHz |
| Cannot bind device | Try mobile hotspot to bypass corporate firewall |
