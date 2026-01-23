# SenseCraft Platform Configuration

Configure SenseCAP Watcher and obtain MCP endpoint for bridge connection.

## Step 1: Power On Watcher

1. Long press power button for 3 seconds to turn on
2. Scan QR code on screen to connect WiFi (requires 2.4GHz network)

## Step 2: Bind to Platform

1. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/home)
2. Click **Add Device**, scan binding QR code on Watcher

## Step 3: Get MCP Endpoint (Important)

1. Go to **Watcher Agent** -> **Configuration**
2. Copy the **MCP Endpoint** address (`wss://...`)

> Save this address - you'll need it for the next step

## Troubleshooting

| Issue | Solution |
|-------|----------|
| WiFi connection failed | Ensure using 2.4GHz network, not 5GHz |
| Cannot bind device | Try using mobile hotspot to bypass office network restrictions |
