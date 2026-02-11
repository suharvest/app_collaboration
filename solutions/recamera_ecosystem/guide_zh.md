## 套餐: 快速预览 {#simple}

只用一台 reCamera，在网页上直接看热力图。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别画面中的人 |

**部署完成后你可以：**
- 看到叠加热力图的实时视频（热力图在网页端实时生成）
- 直观看出哪里人多哪里人少
- 隐私保护（人脸自动打码）

**前提条件：** 新设备需先开启 SSH——用 USB 连接电脑，等设备开机（约 2 分钟），访问 [192.168.42.1/#/security](http://192.168.42.1/#/security)，输入初始账号 `recamera` / `recamera`，打开 SSH 开关

## 步骤 1: 让摄像头能识别人 {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

给 reCamera 安装人员识别程序，让它能在画面中找到人。

### 部署目标: YOLO11 (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

推荐大多数场景使用。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，密码 `recamera`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

### 部署目标: YOLOv26 (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

备选模型，可自行尝试。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，密码 `recamera`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看实时热力图 {#preview type=preview required=false config=devices/preview.yaml}

点击 **连接** 查看带热力图叠加的实时视频。

**提示：** 热力图会随时间累积，等几分钟效果更明显。

**注意：** 热力图渲染需要 ffmpeg，打开终端安装：
- **Windows:** 打开 PowerShell，运行 `winget install ffmpeg`
- **macOS:** 打开终端，运行 `brew install ffmpeg`
- **Linux:** 打开终端，运行 `sudo apt install ffmpeg`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 黑屏 | 等 10 秒让视频流加载；检查摄像头 IP 是否正确 |
| 没有热力图叠加 | 等几分钟让数据积累；确认步骤 1 已完成 |
| ffmpeg 报错 | 按上方说明安装 ffmpeg |

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时热力图。

热力图会随时间累积——人停留越久的区域会越亮。

---

## 套餐: Home Assistant 集成 {#ha_integration}

将 reCamera 接入 Home Assistant，统一管理智能家居设备。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，支持 YOLO 识别 + RTSP 视频流 |
| 电脑 或 reComputer R1100 | 运行 Home Assistant |

**部署完成后你可以：**
- 在 HA 面板中查看实时 RTSP 视频流
- 看到 AI 识别计数传感器，包含各类别明细（人、车等）
- 在 reCamera 上使用 FlowFuse Dashboard 进行本地调试

**前提条件：** Docker 已安装 · 所有设备在同一局域网

---

## 步骤 1: 部署 Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant.yaml}

启动 Home Assistant。如果你已有 HA，可以跳过这一步。

### 部署目标: 在本机运行 {#ha_local type=local config=devices/homeassistant.yaml default=true}

### 接线

1. 确保 Docker Desktop 已安装并运行
2. 至少 2GB 可用磁盘空间

### 部署完成

1. 在浏览器打开 **http://localhost:8123**
2. 按照引导向导创建管理员账号
3. 请记住用户名和密码——步骤 3 需要用到

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口 8123 被占用 | 关闭占用 8123 端口的程序，或修改 docker-compose.yml 中的端口 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确保电脑有至少 2GB 可用内存 |

### 部署目标: 在其他设备运行 {#ha_remote type=remote config=devices/homeassistant_remote.yaml}

### 接线

1. 将目标设备连接到网络
2. 在下方输入 IP 地址、用户名和密码

### 部署完成

1. 在浏览器打开 **http://\<设备IP\>:8123**
2. 按照引导向导创建管理员账号
3. 请记住用户名和密码——步骤 3 需要用到

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试 |
| SSH 认证失败 | 确认用户名密码正确 |

---

## 步骤 2: 部署 AI 识别流程 {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

给 reCamera 安装 YOLO 识别 + RTSP 视频流程序。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，密码 `recamera`

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 3: 在 Home Assistant 中添加 reCamera {#configure_ha type=ha_integration required=true config=devices/homeassistant_existing.yaml}

安装 reCamera 集成并连接到 Home Assistant。

### 接线

1. 输入 Home Assistant 的 **IP 地址**（如 `192.168.1.100`）
2. 输入 HA 设置时创建的**登录用户名和密码**
3. 输入 **reCamera 的 IP 地址** — USB 连接用 `192.168.42.1`，或路由器中查到的 WiFi IP
4. **HA OS 用户**：SSH 相关字段留空 — 系统会自动安装配置 SSH
5. **Docker HA 用户**：还需要填写**宿主机**的 SSH 用户名和密码（不是 HA 的登录密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| HA 登录失败 | 这里填的是 HA 网页登录的用户名密码，不是 SSH 的。请确认是否正确 |
| 重启时间很长 | HA OS 会重启整个系统，可能需要 30-90 秒，请耐心等待 |
| SSH 插件安装失败 | HA OS 需要联网才能下载 SSH 插件，检查网络连接 |
| 文件复制失败 | HA OS 检查磁盘空间；Docker 确认 SSH 凭据是**宿主机**的 |
| 添加后显示 `setup_retry` | HA 无法访问 reCamera — 确保两者在同一局域网 |
| 摄像头缩略图空白，但直播正常 | 已知问题：ffmpeg 截图可能超时，面板中的实时画面不受影响 |
| 传感器显示 0 | 摄像头视野内没有可识别物体时属正常；可访问 http://\<reCamera IP\>:1880/data 验证 |

---

# 部署完成

reCamera 已成功接入 Home Assistant！

## 快速验证

1. 打开 **http://\<服务器IP\>:8123**
2. 进入 **设置 → 设备与服务** — 应该能看到 **reCamera (你的IP)** 设备
3. 点击进入设备查看两个实体
4. 在面板中添加 **图片实体** 卡片来显示摄像头画面

## 访问地址

- **Home Assistant**：http://\<服务器IP\>:8123 — 统一智能家居面板
- **FlowFuse Dashboard**：http://\<reCamera IP\>:1880/dashboard — reCamera 本地调试界面
- **识别数据 API**：http://\<reCamera IP\>:1880/data — 原始识别 JSON 数据

## 后续玩法

- 用识别传感器创建**自动化**（例如检测到人时自动开灯）
- 在面板中用 **图片实体** 或 **图片概览** 卡片添加摄像头画面
- 设置**手机通知**，检测到特定物体时推送提醒

**遇到问题？**
- 看不到画面？检查 reCamera IP，确认步骤 2 已完成
- 没有识别数据？确保视野内有物体；访问 http://\<reCamera IP\>:1880 检查 Node-RED
