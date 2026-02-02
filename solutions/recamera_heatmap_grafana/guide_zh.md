这个方案帮你看清店里哪里人多、哪里人少，用热力图直观展示。

**工作原理：**
1. reCamera 识别画面中的人（自动打码保护隐私）
2. 位置数据发送到你的电脑
3. 你能看到一张「热力地图」，红色代表人多，蓝色代表人少

## 网络要求

确保 reCamera 和电脑在**同一个 WiFi 网络**中。

## 套餐: 快速预览 {#simple}

直接在 reCamera 的网页界面查看热力图，无需额外电脑或后台服务。

| 设备 | 用途 |
|------|------|
| reCamera | 带人员识别功能的 AI 摄像头 |

**部署完成后你可以：**
- 观看叠加热力图的实时视频
- 直观看出哪里人多哪里人少
- 隐私保护（自动模糊人脸）

**前提条件：** reCamera 和电脑在同一网络

## 连接方式

| 方式 | IP 地址 | 说明 |
|------|---------|------|
| USB 线 | 192.168.42.1 | 用 USB-C 线直接连电脑 |
| 网线 | 查看路由器 | 最稳定 |
| WiFi | 查看路由器 | 可能需要先用 USB 配置 |

## 登录信息

- **用户名**: `recamera`
- **密码**: `recamera` 或 `recamera.2`

## 步骤 1: 让摄像头能识别人 {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

给 reCamera 安装人员识别程序，让它能在画面中找到人。

### 部署目标: 高精度模式 (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

识别更准确，适合大多数场景。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | 检查 IP 地址和网络 |
| 密码错误 | 试试 `recamera` 或 `recamera.2` |
| 安装失败 | 重启摄像头再试一次 |

### 部署目标: 流畅模式 (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

精度稍低但更省资源，摄像头运行卡顿时选这个。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | 检查 IP 地址和网络 |
| 密码错误 | 试试 `recamera` 或 `recamera.2` |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看实时热力图 {#preview type=preview required=false config=devices/preview.yaml}

点击 **连接** 查看带热力图叠加的实时视频。

**提示：** 热力图会随时间累积，等几分钟效果更明显。

---

## 套餐: 数据看板 {#grafana}

保存历史数据，用图表查看一段时间内的人流趋势。

| 设备 | 用途 |
|------|------|
| reCamera | 带人员识别功能的 AI 摄像头 |
| reComputer R1100 | 运行 Grafana 看板 + InfluxDB |

**部署完成后你可以：**
- 查看历史人流数据的时序图表
- 自定义 Grafana 看板
- 导出数据做进一步分析

**前提条件：** Docker 已安装 · 所有设备在同一网络

## 网络要求

确保 reCamera 和电脑在**同一个 WiFi 网络**中。

## 步骤 1: 启动数据看板 {#backend type=docker_deploy required=true config=devices/backend.yaml}

在你的电脑（或专用服务器）上启动数据存储和图表显示服务。

### 部署目标: 在本机运行 {#backend_local config=devices/backend.yaml default=true}

在当前电脑上运行看板。

### 前提条件

- Docker Desktop 已安装并运行
- 至少 2GB 可用磁盘空间

![接线图](gallery/architecture.svg)

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

### 部署目标: 在其他设备运行 {#backend_remote config=devices/backend_remote.yaml}

在 reComputer R1100 上运行看板，作为专用的边缘部署方案。

### 开始之前

1. 把目标设备连到网络
2. 记下设备的 IP 地址
3. 准备好登录账号密码

### 连接设置

| 字段 | 示例 |
|------|------|
| 设备 IP | 192.168.1.100 |
| 用户名 | recomputer |
| 密码 | 12345678 |

![接线图](gallery/architecture.svg)

---

## 步骤 2: 让摄像头发送数据 {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

告诉 reCamera 把人流数据发到哪里。

输入：
- **reCamera IP**：摄像头的 IP 地址
- **看板服务器 IP**：运行看板的电脑 IP（来自步骤 1）

其他设置已经配好，不用改。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | 检查摄像头和服务器是否在同一网络 |
| 看不到数据 | 确认步骤 1 已完成 |

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

---

# 部署完成

## 部署完成！

你的实时热力图系统已经在运行了。

### 访问入口

| 服务 | 地址 |
|------|------|
| 数据看板 | http://\<服务器IP\>:3000 |

### 登录信息

- 用户名：`admin`
- 密码：`admin`

看板和数据连接都已配好，打开就能看数据。

### 遇到问题？

- **看不到数据**：检查摄像头是否连上了
- **打不开看板**：用 `docker ps` 看看服务有没有在跑
