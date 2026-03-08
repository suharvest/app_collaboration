## 套餐: OpenClaw + 可选本地模型 {#openclaw_basic}

部署 OpenClaw AI 消息网关，可选利用设备算力运行本地 AI 模型。

| 设备 | 用途 |
|------|------|
| reComputer R 或 Jetson | 运行 OpenClaw 网关和可选的本地 AI 模型 |

**部署完成后你可以：**
- AI 聊天网关支持 20+ 消息平台
- 可选在设备上运行本地模型——对话数据不出内网
- 通过 Web 管理界面进行配置

**前提条件：** 已安装 Docker · 需要联网（首次下载镜像）

## 步骤 1: 部署 OpenClaw {#deploy_openclaw type=docker_deploy required=true config=devices/local.yaml}

部署 OpenClaw（龙虾机器人）AI 网关。如果启用了本地模型，会自动启动并配置好。

### 部署目标: 本机部署 {#local config=devices/local.yaml default=true}

部署在你的 reComputer R 系列设备上。

### 接线

1. 确保 Docker 已安装并运行
2. 可选勾选 **启用本地模型** 并选择模型
3. 点击 **部署** 启动服务

### 部署完成

1. 在浏览器打开 **http://localhost:18789**
2. 按照页面引导完成账号创建
3. 连接你的第一个消息平台（微信、Telegram、Discord 等）
4. 如果启用了本地模型，已自动配置好——创建智能体时选择本地模型即可

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口 18789 被占用 | 停止占用该端口的服务，或检查 OpenClaw 是否已在运行 |
| 找不到 Docker | 安装 Docker Desktop 并确保已启动 |
| 模型下载慢 | 大模型下载需要时间，检查网络连接 |
| OpenClaw 容器反复重启 | 查看日志：`docker logs openclaw-gateway` |

### 部署目标: 远程部署 (Jetson) {#jetson_remote config=devices/jetson.yaml}

通过 SSH 部署到 reComputer Jetson 设备，利用 GPU 加速本地模型。

### 接线

1. 将 reComputer Jetson 连接到同一局域网
2. 输入 Jetson IP 地址、SSH 用户名和密码
3. 可选勾选 **启用本地模型** 并选择模型
4. 点击 **部署** 启动服务

### 部署完成

1. 在浏览器打开 **http://\<Jetson IP\>:18789**
2. 按照页面引导完成账号创建
3. 连接你的第一个消息平台
4. 如果启用了本地模型，已自动配置好并使用 GPU 加速——创建智能体时选择本地模型即可

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 Jetson IP 地址、用户名、密码和 SSH 服务是否运行 |
| 未检测到 NVIDIA 运行时 | 确保已安装 NVIDIA 容器运行时：`nvidia-smi` 应能正常执行 |
| Docker Compose 不可用 | 安装：`sudo apt-get install -y docker-compose-plugin` |
| 模型下载慢 | 首次下载需要获取完整模型，后续使用缓存 |
| 磁盘空间不足 | 至少需要 20GB 空闲空间，用 `df -h /` 检查 |
| 端口 11434 被占用 | 可能已有本地 AI 服务在运行，部署器会自动使用它 |

# 部署完成

OpenClaw（龙虾机器人）AI 网关已部署完成，可以开始使用。

## 初始设置

1. 在浏览器中打开 OpenClaw 管理界面
2. 按照引导向导创建你的账号
3. 连接你的第一个消息平台（微信、Telegram、Discord 等）

## 快速验证

- 管理界面正常加载
- 如果启用了本地模型：进入 设置 > 模型，应该能看到本地模型提供者
- 通过已连接的消息平台发送一条测试消息

## 后续步骤

- [OpenClaw 文档](https://github.com/nicepkg/openclaw)
- 在 设置 > 模型 中添加更多 AI 提供者
- 连接更多消息平台
