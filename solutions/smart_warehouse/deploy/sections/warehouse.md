# Warehouse Management System

Provides REST APIs for inventory management, stock-in/out operations. This is the business backend for the voice control solution.

## Post-Deployment Setup

After deployment, complete these manual steps:

### 1. Create Admin Account

1. Open `http://localhost:2125`
2. Enter username and password, click **Register**

> The first registered user becomes administrator

### 2. Create API Key

1. After login, go to **User Management**
2. In **API Key Management**, enter a key name
3. Click **Create API Key**
4. **Copy the key immediately** (format: `wh_xxxx...`, shown only once)

## Verification

- Web interface: `http://localhost:2125`
- API docs: `http://localhost:2124/docs`
