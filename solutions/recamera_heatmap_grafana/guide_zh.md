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

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时热力图。

热力图会随时间累积——人停留越久的区域会越亮。

---

## 套餐: 数据看板 {#grafana}

加一台电脑跑看板，保存历史数据，随时回看人流变化。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别人并发送位置数据 |
| 电脑 或 reComputer R1100 | 运行 Grafana 看板 + InfluxDB |

**部署完成后你可以：**
- 用图表看一天、一周的人流变化
- 自定义看板布局
- 导出数据做分析

**前提条件：** Docker 已安装 · 所有设备在同一网络

## 步骤 1: 启动数据看板 {#backend type=docker_deploy required=true config=devices/backend.yaml}

在你的电脑（或专用服务器）上启动数据存储和图表显示服务。

### 部署目标: 在本机运行 {#backend_local type=local config=devices/backend.yaml default=true}

### 接线

![接线图](gallery/architecture.svg)

确保 Docker Desktop 已安装并运行，至少 2GB 可用磁盘空间。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

### 部署目标: 在其他设备运行 {#backend_remote type=remote config=devices/backend_remote.yaml}

### 接线

![接线图](gallery/architecture.svg)

| 字段 | 示例 |
|------|------|
| 设备 IP | 192.168.1.100 或 reComputer-R110x.local |
| 用户名 | recomputer |
| 密码 | 12345678 |

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试 |
| SSH 认证失败 | 确认用户名密码正确 |

---

## 步骤 2: 让摄像头发送数据 {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

告诉 reCamera 把人流数据发到哪里。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入 reCamera IP 和看板服务器 IP（来自步骤 1）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 看不到数据 | 确认步骤 1 已完成，reCamera 和服务器在同一网络 |

---

## 步骤 3: 把热力图叠加到平面图（可选） {#heatmap type=manual required=false}

把热力图显示在你店铺的平面图上。

### 操作步骤

1. **准备图片**
   - 从 reCamera 截一张图
   - 准备店铺平面图

2. **运行校准工具**
   - 运行：`python calibration_tool.py`
   - 在摄像头图片上点 4 个参考点
   - 在平面图上点对应的 4 个位置

3. **查看效果**
   - 运行 `python -m http.server 8080`
   - 浏览器打开 `http://localhost:8080`

### 什么时候可以跳过

如果只想在看板里看摄像头视角的热力图，可以跳过这步。

### 部署完成

热力图看板已就绪！

**访问看板：**
- 地址：http://\<服务器IP\>:3000
- 登录：`admin` / `admin`

看板已配好，打开就能看数据。

**遇到问题？**
- 看不到数据？检查摄像头是否连上了
- 打不开看板？用 `docker ps` 看看服务有没有在跑
