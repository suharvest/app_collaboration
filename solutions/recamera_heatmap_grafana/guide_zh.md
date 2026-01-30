本方案部署一个实时人流分布图系统，包含四个部分：

1. **数据库** - 存储 reCamera 检测到的人流位置数据
2. **reCamera** - 在摄像头端运行人员检测，自动打码后只传位置数据
3. **数据看板** - 用图表展示人流统计和趋势
4. **人流分布图** - 在你的平面图上直观显示人群聚集区域

## 网络要求

确保 reCamera 和你的电脑在**同一个 WiFi 网络**中。这样才能：
- reCamera 把数据发送到你的电脑
- 数据看板显示来自 reCamera 的实时画面
- 人流分布图从数据库读取位置信息

## 套餐: 简单预览 {#simple}

将热力图应用部署到 reCamera，实现实时人员检测和热力可视化。无需后端服务器。

## 连接方式

| 方式 | IP 地址 | 说明 |
|------|---------|------|
| USB 连接 | 192.168.42.1 | 直接 USB-C 连接 |
| 有线网络 | 查看路由器 | 最稳定 |
| WiFi | 查看路由器 | 可能需要先通过 USB 配置 |

## 默认凭证

- **用户名**: `recamera`
- **密码**: `recamera` 或 `recamera.2`

## 步骤 1: 部署检测器 {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

### 部署目标: YOLO11 (~8 FPS) {#deploy_detector_yolo11 config=devices/recamera_yolo11.yaml default=true}

YOLO11 使用 DFL (Distribution Focal Loss) 进行更精确的边界框回归，在 reCamera 上可达 **~8 FPS**。

### 注意

部署完成后，在预览步骤中使用 MQTT 主题 `recamera/yolo11/detections`。

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 检查 IP 地址和网络连接 |
| 认证失败 | 尝试密码 `recamera` 或 `recamera.2` |
| 软件包安装失败 | 重启设备后重试 |
| 与 YOLO26 冲突 | YOLO11 部署会自动停止 YOLO26 服务 |

### 部署目标: YOLO26 (~3 FPS) {#deploy_detector_yolo26 config=devices/recamera_yolo26.yaml}

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 检查 IP 地址和网络连接 |
| 认证失败 | 尝试密码 `recamera` 或 `recamera.2` |
| 软件包安装失败 | 重启设备后重试 |

---

## 步骤 2: 热力图实时预览 {#preview type=preview required=false config=devices/preview.yaml}

点击 **连接** 查看带有热力图叠加的实时视频。

**提示：** 热力图会随时间累积，等待几分钟让它建立起来。

---

## 套餐: Grafana 仪表板 {#grafana}

本方案部署一个实时人流分布图系统，包含四个部分：

1. **数据库** - 存储 reCamera 检测到的人流位置数据
2. **reCamera** - 在摄像头端运行人员检测，自动打码后只传位置数据
3. **数据看板** - 用图表展示人流统计和趋势
4. **人流分布图** - 在你的平面图上直观显示人群聚集区域

## 网络要求

确保 reCamera 和你的电脑在**同一个 WiFi 网络**中。这样才能：
- reCamera 把数据发送到你的电脑
- 数据看板显示来自 reCamera 的实时画面
- 人流分布图从数据库读取位置信息

## 步骤 1: 部署 InfluxDB + Grafana {#backend type=docker_deploy required=true config=devices/backend.yaml}

### 部署目标: 本机部署 {#backend_local config=devices/backend.yaml default=true}

## 本机部署

将数据库和数据看板服务部署到您的电脑上。

### 前提条件

- Docker Desktop 已安装并运行
- 至少 2GB 可用磁盘空间
- 端口 8086 和 3000 未被占用

![接线图](intro/gallery/architecture.svg)

1. 确保 Docker 已安装并运行
2. 点击部署按钮启动服务

#### 故障排除

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 部署失败提示端口占用 | 8086 或 3000 端口被其他程序使用 | 关闭占用端口的程序，或在配置中修改端口 |
| Docker 无法启动 | Docker Desktop 未运行 | 打开 Docker Desktop 应用 |
| 容器启动后自动停止 | 内存不足 | 确保电脑有至少 4GB 可用内存 |

### 部署目标: 远程部署 {#backend_remote config=devices/backend_remote.yaml}

# 远程部署

将 InfluxDB 和 Grafana 部署到远程设备（reComputer、树莓派等）。

## 开始之前

1. **将目标设备连接到网络**
   - 确保设备与您的电脑在同一网络
   - 记录设备的 IP 地址

2. **获取设备凭据**
   - SSH 用户名（通常是 `root`、`pi` 或 `recomputer`）
   - SSH 密码

## 连接设置

填写以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| 设备 IP | 目标设备 IP 地址 | 192.168.1.100 |
| SSH 用户名 | 登录用户名 | root |
| SSH 密码 | 登录密码 | your-password |
| SSH 端口 | SSH 端口（默认 22） | 22 |

## 部署完成后

访问 InfluxDB：`http://<设备IP>:8086`
- 账号：admin / adminpassword
- 组织：seeed，存储桶：recamera

进入 **API Tokens** 复制令牌，后续配置需要。

访问 Grafana：`http://<设备IP>:3000`
- 默认账号：admin / admin

![接线图](intro/gallery/architecture.svg)

1. 将目标设备连接到网络
2. 输入 IP 地址和 SSH 凭据
3. 点击部署安装到远程设备

---

## 步骤 2: 配置 reCamera {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

## 配置 reCamera

让 reCamera 把检测到的人流数据发送到数据库。

### 操作步骤

1. 访问 [SenseCraft reCamera](https://sensecraft.seeed.cc/ai/recamera)，部署人流分布图应用到 reCamera
2. 进入 reCamera 的 Node-RED 界面，安装 `node-red-contrib-influxdb` 节点
3. 配置数据库节点：
   - URL 填写 `http://<你的电脑IP>:8086`
   - 粘贴上一步获取的 API 令牌
4. 点击 Deploy 部署流程

### 故障排除

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 节点安装失败 | 网络问题 | 检查 reCamera 是否能访问外网 |
| 连接数据库失败 | IP 地址错误 | 确认电脑 IP 地址，确保 reCamera 和电脑在同一网络 |
| 数据库无数据 | Token 无效 | 重新从数据库获取 API 令牌 |

---

## 步骤 3: 配置 Grafana 仪表板 {#grafana_config type=manual required=true}

## 配置数据看板

将数据库连接到 Grafana 数据看板，导入预设的图表模板。

### 操作步骤

1. 打开浏览器访问 `http://localhost:3000`
2. 使用默认账号登录：admin / admin
3. 添加数据源：
   - 进入 **Connections** > **Data sources** > 点击 **Add data source**
   - 选择 **InfluxDB**
   - Query Language 选择 **Flux**
   - URL 填写 `http://influxdb:8086`
   - 粘贴之前复制的 API 令牌
   - 点击 **Save & Test**
4. 导入图表模板：
   - 进入 **Dashboards** > **Import**
   - 上传方案提供的仪表板 JSON 文件

### 故障排除

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 无法访问 localhost:3000 | 服务未启动 | 返回上一步检查部署状态 |
| 数据源测试失败 | Token 不正确 | 重新从数据库复制完整的 API 令牌 |
| 图表显示无数据 | reCamera 未发送数据 | 检查 reCamera 的 Node-RED 是否正常运行 |

---

## 步骤 4: 校准并配置热力图 {#heatmap type=manual required=true}

## 配置人流分布图

校准摄像头视角与实际平面图的对应关系，让人流数据能正确显示在平面图上。

### 操作步骤

1. **准备素材**
   - 从 reCamera 导出一张截图
   - 准备你的店铺/场地平面图

2. **校准对应点**
   - 运行校准工具：`python calibration_tool.py`
   - 在摄像头截图上点击 4 个角落参考点
   - 在平面图上点击对应的 4 个位置
   - 工具会自动生成校准代码

3. **配置页面**
   - 将生成的校准代码粘贴到 `index.html` 文件
   - 填写数据库连接信息（IP、Token）

4. **启动服务**
   - 运行 `python -m http.server 8080`
   - 浏览器访问 `http://localhost:8080` 查看效果

### 故障排除

### 故障排查

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 人流位置显示偏移 | 校准点选取不准确 | 重新运行校准工具，选择更明显的参考点 |
| 页面显示空白 | 数据库连接失败 | 检查 Token 和 IP 地址是否正确 |
| 数据有延迟 | 网络问题 | 检查网络连接稳定性 |

---

# 部署完成

## 部署完成！

您的实时热力图系统现已运行。

### 访问入口

| 服务 | URL |
|------|-----|
| Grafana 仪表板 | http://localhost:3000 |
| 热力图页面 | http://localhost:8080/index.html |
| InfluxDB 界面 | http://localhost:8086 |

### Grafana 登录

- 用户名：`admin`
- 密码：`admin`（首次登录时更改）

### 下一步

1. **校准热力图** - 运行 Python 校准工具，将相机坐标映射到您的平面图
2. **自定义仪表板** - 添加或修改 Grafana 面板以满足您的需求
3. **调整热力图设置** - 在 index.html 中配置刷新间隔和累积模式

### 故障排除

- **Grafana 中没有数据**：检查 reCamera 是否已连接且 Node-RED 流程已部署
- **热力图无法加载**：验证 index.html 中的 InfluxDB 凭据
- **视频流断开**：这是正常的，由于 reCamera 资源限制；它会自动重新连接
