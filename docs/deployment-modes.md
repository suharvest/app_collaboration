# SenseCraft Solution 部署模式指南

本文档整理了系统支持的所有部署类型，包括配置方式和所需准备的文件清单，方便团队协作和工作量评估。

> **注意**：方案配置的整体结构请参考 [solution-configuration-guide.md](./solution-configuration-guide.md)。本文档专注于 `devices/*.yaml` 设备配置文件的详细说明。

---

## 目录

1. [部署模式总览](#部署模式总览)
2. [ESP32 USB 烧录](#1-esp32-usb-烧录-esp32_usb)
3. [Himax USB 烧录](#2-himax-usb-烧录-himax_usb)
4. [本地 Docker 部署](#3-本地-docker-部署-docker_local)
5. [远程 Docker 部署](#4-远程-docker-部署-docker_remote)
6. [SSH Deb 包部署](#5-ssh-deb-包部署-ssh_deb)
7. [本地脚本部署](#6-本地脚本部署-script)
8. [手动部署](#7-手动部署-manual)
9. [reCamera Node-RED 部署](#8-recamera-node-red-部署-recamera_nodered)
10. [reCamera C++ 应用部署](#9-recamera-c-应用部署-recamera_cpp)
11. [实时预览](#10-实时预览-preview)
12. [工作量估算](#工作量估算)
13. [协作分工建议](#协作分工建议)

---

## 部署模式总览

| 类型 | 用途 | 目标平台 | 复杂度 |
|------|------|----------|--------|
| `esp32_usb` | ESP32 固件烧录 | ESP32/ESP32-S3 设备 | ⭐⭐ |
| `himax_usb` | Himax WE2 固件烧录 | Grove Vision AI V2 / SenseCAP Watcher | ⭐⭐ |
| `docker_local` | 本地 Docker 部署 | 运行本应用的电脑 | ⭐ |
| `docker_deploy` | Docker 部署（支持本地/远程） | 本地或远程 Linux 设备 | ⭐⭐ |
| `docker_remote` | 远程 Docker 部署 | 远程 Linux 设备（SSH） | ⭐⭐ |
| `ssh_deb` | deb 包安装 | 远程 Linux 设备（SSH） | ⭐⭐⭐ |
| `script` | 本地脚本执行 | 运行本应用的电脑 | ⭐⭐ |
| `manual` | 手动操作指引 | 任何（用户自行完成） | ⭐ |
| `recamera_nodered` | Node-RED Flow 部署 | reCamera 设备 | ⭐⭐ |
| `recamera_cpp` | C++ 应用部署 | reCamera 设备 | ⭐⭐⭐ |
| `preview` | 实时视频/数据预览 | reCamera 等设备 | ⭐ |

---

## 1. ESP32 USB 烧录 (`esp32_usb`)

### 概述

通过 USB 串口使用 esptool 烧录 ESP32 固件。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（芯片型号、分区表） |
| `assets/firmware/*.bin` | ✅ | 固件开发 | 编译好的固件文件 |
| `assets/firmware/bootloader.bin` | ❌ | 固件开发 | 多分区时需要 |
| `assets/firmware/partition-table.bin` | ❌ | 固件开发 | 多分区时需要 |

**需要确认的参数**：
- 芯片型号（esp32/esp32s3/esp32c3）
- Flash 大小（4MB/8MB/16MB/32MB）
- USB Vendor ID 和 Product ID
- 分区地址偏移量

### 配置文件示例

```yaml
# devices/watcher_esp32.yaml
version: "1.0"
id: watcher_esp32
name: SenseCAP Watcher ESP32
name_zh: SenseCAP Watcher ESP32 固件
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x1a86"      # USB Vendor ID
  usb_product_id: "0x55d2"     # USB Product ID
  fallback_ports:              # 备用串口匹配模式
    - "/dev/tty.wchusbserial*"
    - "/dev/cu.wchusbserial*"
    - "/dev/ttyUSB*"
    - "COM*"                   # Windows

firmware:
  source:
    type: local                # local | url | github_release
    path: assets/firmware/merged-binary.bin
  flash_config:
    chip: esp32s3              # esp32 | esp32s3 | esp32c3
    baud_rate: 921600
    flash_mode: dio
    flash_freq: 80m
    flash_size: 16MB
    partitions:
      - name: merged_firmware
        offset: "0x0"
        file: merged-binary.bin
      # 多分区示例：
      # - name: bootloader
      #   offset: "0x0"
      #   file: bootloader.bin
      # - name: partition_table
      #   offset: "0x8000"
      #   file: partition-table.bin
      # - name: app
      #   offset: "0x10000"
      #   file: app.bin

user_inputs:
  - id: serial_port
    name: Serial Port
    name_zh: 串口
    type: serial_port          # 特殊类型：串口选择器
    required: true
    auto_detect: true

steps:
  - id: detect
    name: Detect Chip
    name_zh: 检测芯片
  - id: erase                  # 可选步骤
    name: Erase Flash
    name_zh: 擦除闪存
    optional: true
    default: false
  - id: flash
    name: Flash Firmware
    name_zh: 烧录固件
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  reset_device: true
  wait_for_ready: 3
```

---

## 2. Himax USB 烧录 (`himax_usb`)

### 概述

通过 USB 使用 xmodem 协议烧录 Himax WE2 固件（Grove Vision AI V2 / SenseCAP Watcher 的协处理器）。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/firmware/*.img` | ✅ | 固件开发 | Himax 固件文件 |
| `assets/models/*.tflite` | ❌ | AI 开发 | TFLite 模型文件 |

### 配置文件示例

```yaml
# devices/watcher_himax.yaml
version: "1.0"
id: watcher_himax
name: SenseCAP Watcher Himax
name_zh: SenseCAP Watcher 人脸识别固件
type: himax_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x2886"
  usb_product_id: "0x8060"
  fallback_ports:
    - "/dev/tty.usbmodem*"
    - "/dev/cu.usbmodem*"

firmware:
  source:
    type: local
    path: assets/firmware/firmware.img
  flash_config:
    protocol: xmodem
    baud_rate: 921600

user_inputs:
  - id: serial_port
    name: Serial Port
    name_zh: 串口
    type: serial_port
    required: true
    auto_detect: true

post_deployment:
  reset_device: true
```

---

## 3. 本地 Docker 部署 (`docker_local`)

### 概述

在运行本应用的电脑上通过 Docker Compose 启动容器服务。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/docker/docker-compose.yml` | ✅ | 后端开发 | Docker Compose 配置 |
| `assets/docker/Dockerfile` | ❌ | 后端开发 | 如需本地构建镜像 |
| `assets/docker/.env.example` | ❌ | 后端开发 | 环境变量示例 |

**需要确认的参数**：
- Docker 镜像名称和版本
- 暴露的端口号
- 健康检查端点
- 需要用户输入的环境变量

### 配置文件示例

```yaml
# devices/backend_local.yaml
version: "1.0"
id: backend_local
name: Backend Services (Local)
name_zh: 后端服务（本机）
type: docker_local

detection:
  method: local
  requirements:
    - docker_installed
    - docker_running

docker:
  compose_file: assets/docker/docker-compose.yml

  environment:
    TZ: Asia/Shanghai
    DB_USER: admin
    DB_PASSWORD: "{{db_password}}"  # 支持用户输入变量

  options:
    project_name: my-project
    remove_orphans: true
    build: false

  services:
    - name: api
      port: 8080
      health_check_endpoint: /health
      required: true
    - name: web
      port: 3000
      health_check_endpoint: /
      required: false

  images:
    - name: seeedcloud/my-api
      required: true
    - name: seeedcloud/my-web
      required: true

user_inputs:
  - id: db_password
    name: Database Password
    name_zh: 数据库密码
    type: password
    required: true
    default: "admin123"

pre_checks:
  - type: docker_version
    min_version: "20.0"
  - type: port_available
    ports: [8080, 3000]

steps:
  - id: pull_images
    name: Pull Docker images
    name_zh: 拉取镜像
  - id: create_volumes
    name: Create volumes
    name_zh: 创建数据卷
  - id: start_services
    name: Start services
    name_zh: 启动服务
  - id: health_check
    name: Health check
    name_zh: 健康检查

post_deployment:
  open_browser: true
  url: http://localhost:8080
  credentials:
    username: admin
    password: admin123
```

---

## 4. 远程 Docker 部署 (`docker_remote`)

### 概述

通过 SSH 连接到远程 Linux 设备，上传 docker-compose 文件并启动容器。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（含 SSH 配置） |
| `assets/docker/docker-compose.yml` | ✅ | 后端开发 | Docker Compose 配置 |
| `assets/docker/*` | ❌ | 后端开发 | 其他需要上传的文件 |

**需要确认的参数**：
- 目标设备架构（arm64/amd64）
- 默认 SSH 用户名
- 远程部署路径
- 是否需要自动安装 Docker

### 配置文件示例

```yaml
# devices/backend_remote.yaml
version: "1.0"
id: backend_remote
name: Backend Services (Remote)
name_zh: 后端服务（远程）
type: docker_ssh

detection:
  method: ssh
  requirements:
    - ssh_reachable
    - docker_installed

ssh:
  port: 22
  username: root
  connection_timeout: 30
  command_timeout: 600         # 拉取镜像可能较慢

docker:
  compose_file: assets/docker/docker-compose.yml
  compose_dir: assets/docker   # 上传整个目录

  remote_path: /home/{{username}}/myapp

  environment:
    TZ: Asia/Shanghai
    DEVICE_NAME: "{{device_name}}"

  options:
    project_name: myapp
    remove_orphans: true

  services:
    - name: app
      port: 8080
      health_check_endpoint: /health
      required: true

user_inputs:
  - id: host
    name: Device IP
    name_zh: 设备 IP
    type: text
    required: true
    placeholder: "192.168.1.100"
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

  - id: username
    name: SSH Username
    name_zh: SSH 用户名
    type: text
    default: root
    required: true

  - id: password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    required: true

  - id: device_name
    name: Device Name
    name_zh: 设备名称
    type: text
    default: "Edge Device"

steps:
  - id: connect
    name: SSH Connect
    name_zh: SSH 连接
  - id: check_docker
    name: Check Docker
    name_zh: 检查 Docker
  - id: prepare
    name: Prepare Directory
    name_zh: 准备目录
  - id: upload
    name: Upload Files
    name_zh: 上传文件
  - id: pull_images
    name: Pull Images
    name_zh: 拉取镜像
  - id: start_services
    name: Start Services
    name_zh: 启动服务
  - id: health_check
    name: Health Check
    name_zh: 健康检查

post_deployment:
  open_browser: true
  url: "http://{{host}}:8080"
```

---

## 5. SSH Deb 包部署 (`ssh_deb`)

### 概述

通过 SSH 连接到远程 Linux 设备，上传并安装 .deb 包，配置 systemd 服务。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（含 SSH 配置） |
| `assets/packages/xxx.deb` | ✅ | 后端开发 | Debian 安装包 |
| `assets/config/*` | ❌ | 后端开发 | 配置文件（如需要） |

**需要确认的参数**：
- 目标架构（arm64/amd64/armhf）
- systemd 服务名称
- 配置文件路径

### 配置文件示例

```yaml
# devices/gateway.yaml
version: "1.0"
id: gateway
name: IoT Gateway
name_zh: IoT 网关
type: ssh_deb

detection:
  method: network_scan
  manual_entry: true

ssh:
  port: 22
  default_user: root
  connection_timeout: 30
  command_timeout: 300

package:
  source:
    type: local
    path: assets/packages/myapp_1.0.0_arm64.deb
    checksum:
      sha256: "abc123..."

  install_commands:
    - "dpkg -i {package}"
    - "apt-get install -f -y"

  config_files:
    - source: assets/config/app.yaml
      destination: /etc/myapp/config.yaml
      mode: "0644"

  service:
    name: myapp
    enable: true
    start: true

user_inputs:
  - id: host
    name: Device IP
    name_zh: 设备 IP
    type: text
    required: true

  - id: password
    name: Root Password
    name_zh: Root 密码
    type: password
    required: true

steps:
  - id: connect
    name: SSH Connect
    name_zh: SSH 连接
  - id: transfer
    name: Transfer Package
    name_zh: 传输安装包
  - id: install
    name: Install Package
    name_zh: 安装软件包
  - id: configure
    name: Configure
    name_zh: 配置
  - id: start_service
    name: Start Service
    name_zh: 启动服务

post_deployment:
  verify_service: true
  service_name: myapp
```

---

## 6. 本地脚本部署 (`script`)

### 概述

在本地执行脚本命令，支持配置文件生成和健康检查。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/project/*` | ✅ | 应用开发 | 项目代码/脚本 |

**需要确认的参数**：
- 运行环境要求（Node.js/Python 版本等）
- 启动命令（Linux/macOS 和 Windows）
- 健康检查方式（日志匹配/HTTP/进程）

### 配置文件示例

```yaml
# devices/mcp_bridge.yaml
version: "1.0"
id: mcp_bridge
name: MCP Bridge Server
name_zh: MCP 桥接服务
type: script

detection:
  method: local
  requirements: []

script:
  working_dir: assets/mcp_bridge

  setup_commands:
    - command: "npm install"
      description: "Install dependencies"
    - command: "npm run build"
      description: "Build project"

  config_template:
    file: .env
    content: |
      API_KEY={{api_key}}
      SERVER_URL={{server_url}}
      DEBUG={{debug_mode}}

  start_command:
    linux_macos: "npm start"
    windows: "npm.cmd start"
    env:
      NODE_ENV: production
      PORT: "3000"

  health_check:
    type: log_pattern
    pattern: "Server listening on port"
    timeout_seconds: 30
    # 或 HTTP 检查：
    # type: http
    # url: http://localhost:3000/health

user_inputs:
  - id: api_key
    name: API Key
    name_zh: API 密钥
    type: password
    required: true

  - id: server_url
    name: Server URL
    name_zh: 服务器地址
    type: text
    default: "http://localhost:8080"

  - id: debug_mode
    name: Debug Mode
    name_zh: 调试模式
    type: checkbox
    default: "false"

steps:
  - id: validate
    name: Validate Environment
    name_zh: 验证环境
  - id: setup
    name: Run Setup
    name_zh: 执行安装
  - id: configure
    name: Generate Config
    name_zh: 生成配置
  - id: start
    name: Start Service
    name_zh: 启动服务
  - id: health_check
    name: Health Check
    name_zh: 健康检查

post_deployment:
  open_browser: true
  url: http://localhost:3000
```

---

## 7. 手动部署 (`manual`)

### 概述

仅显示操作指南，用户手动完成配置。适用于无法自动化的步骤。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置（最简） |
| guide.md 中的说明 | ✅ | 详细操作指南 |
| `gallery/*.png` | ❌ | 操作截图 |

### 配置文件示例

```yaml
# devices/manual_config.yaml
version: "1.0"
id: manual_config
name: Manual Configuration
name_zh: 手动配置
type: manual

detection:
  method: local
  requirements: []

# manual 类型几乎不需要其他配置
# 主要靠 guide.md 中的说明文字

steps:
  - id: manual_steps
    name: Follow Instructions
    name_zh: 按照指引操作
```

---

## 8. reCamera Node-RED 部署 (`recamera_nodered`)

### 概述

通过 Node-RED Admin HTTP API 部署 Flow 到 reCamera 设备。自动处理冲突服务和配置更新。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/nodered/flow.json` | ✅ | Node-RED 开发 | 导出的 Flow 文件 |

**需要确认的参数**：
- InfluxDB 节点 ID（如需自动配置）
- 需要停止的冲突服务列表

**Flow 导出方法**：
1. 在 Node-RED 编辑器中设计好 Flow
2. 选择所有节点 → 菜单 → Export → Download

### 配置文件示例

```yaml
# devices/recamera_nodered.yaml
version: "1.0"
id: recamera_nodered
name: reCamera Node-RED
name_zh: reCamera Node-RED 配置
type: recamera_nodered

detection:
  method: network_scan
  manual_entry: true

nodered:
  flow_file: assets/nodered/flow.json
  port: 1880
  influxdb_node_id: "069087e0ad1b172e"

user_inputs:
  - id: recamera_ip
    name: reCamera IP
    name_zh: reCamera IP 地址
    type: text
    required: true
    placeholder: "192.168.42.1"

  - id: ssh_password
    name: SSH Password (Optional)
    name_zh: SSH 密码（可选）
    type: password
    required: false
    description: Required to stop conflicting C++ services

  - id: influxdb_url
    name: InfluxDB URL
    name_zh: InfluxDB 地址
    type: text
    placeholder: "http://192.168.1.100:8086"

  - id: influxdb_token
    name: InfluxDB Token
    name_zh: InfluxDB 令牌
    type: password

  - id: influxdb_org
    name: InfluxDB Organization
    name_zh: InfluxDB 组织
    type: text
    default: "seeed"

  - id: influxdb_bucket
    name: InfluxDB Bucket
    name_zh: InfluxDB 存储桶
    type: text
    default: "recamera"

steps:
  - id: prepare
    name: Prepare
    name_zh: 准备
  - id: load_flow
    name: Load Flow
    name_zh: 加载 Flow
  - id: connect
    name: Connect to Node-RED
    name_zh: 连接 Node-RED
  - id: deploy
    name: Deploy Flow
    name_zh: 部署 Flow
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  open_browser: false
```

### 自动处理功能

1. **停止冲突服务**（需要 SSH 密码）：
   - S92yolo26-detector
   - S99sensecraft
   - S99sscma
   - 其他 C++ 应用

2. **配置注入**：
   - 自动更新 Flow 中的 InfluxDB URL
   - 自动设置 InfluxDB Token（通过 credentials API）

---

## 9. reCamera C++ 应用部署 (`recamera_cpp`)

### 概述

通过 SSH + opkg 部署 C++ 应用到 reCamera 设备。支持 deb 包安装、模型文件部署、SysVinit 服务配置。

### 需要提供的文件

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/packages/xxx.deb` | ✅ | 嵌入式开发 | opkg 安装包 |
| `assets/models/*.cvimodel` | ❌ | AI 开发 | 转换后的模型文件 |
| `assets/scripts/init_script` | ❌ | 嵌入式开发 | SysVinit 脚本（如 deb 不包含） |

**需要确认的参数**：
- 服务名称和优先级（S??xxx）
- 模型文件目标路径
- 需要停止/禁用的冲突服务
- 是否需要配置 MQTT 外部访问

### 配置文件示例

```yaml
# devices/yolo_detector.yaml
version: "1.0"
id: yolo_detector
name: YOLO Detector
name_zh: YOLO 检测器
type: recamera_cpp

detection:
  method: network_scan
  manual_entry: true

ssh:
  port: 22
  default_user: recamera
  connection_timeout: 30
  command_timeout: 300

binary:
  deb_package:
    path: assets/packages/yolo26-detector_1.0.0_riscv64.deb
    name: yolo26-detector
    includes_init_script: true

  models:
    - path: assets/models/yolo26.cvimodel
      target_path: /userdata/local/models
      filename: yolo26.cvimodel
    - path: assets/models/config.json
      target_path: /userdata/local/models

  init_script:
    name: yolo26-detector
    priority: 92
    binary_path: /usr/local/bin
    daemon_args: "--config /etc/yolo26/config.json"
    log_file: /var/log/yolo26.log
    ld_library_path: "/mnt/system/lib:/mnt/system/usr/lib"

  mqtt_config:
    enable: true
    port: 1883
    allow_anonymous: true

  conflict_services:
    stop:
      - S03node-red
      - S91sscma-node
      - S93sscma-supervisor
    disable:
      - node-red
      - sscma-node

  auto_start: true
  service_name: yolo26-detector
  service_priority: 92

user_inputs:
  - id: host
    name: reCamera IP
    name_zh: reCamera IP 地址
    type: text
    required: true
    placeholder: "192.168.42.1"

  - id: password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    required: true
    default: "recamera"

steps:
  - id: connect
    name: SSH Connect
    name_zh: SSH 连接
  - id: prepare
    name: Stop Services
    name_zh: 停止服务
  - id: transfer
    name: Transfer Files
    name_zh: 传输文件
  - id: install
    name: Install Package
    name_zh: 安装软件包
  - id: models
    name: Deploy Models
    name_zh: 部署模型
  - id: configure
    name: Configure Service
    name_zh: 配置服务
  - id: mqtt
    name: Configure MQTT
    name_zh: 配置 MQTT
  - id: disable
    name: Disable Conflicts
    name_zh: 禁用冲突服务
  - id: start
    name: Start Service
    name_zh: 启动服务
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  verify_service: true
```

### SysVinit 脚本模板

如果 deb 包不包含启动脚本，需要提供：

```bash
#!/bin/sh
# /etc/init.d/S92yolo26-detector

DAEMON=/usr/local/bin/yolo26-detector
DAEMON_ARGS="--config /etc/yolo26/config.json"
PIDFILE=/var/run/yolo26-detector.pid
LOGFILE=/var/log/yolo26-detector.log

export LD_LIBRARY_PATH=/mnt/system/lib:/mnt/system/usr/lib

case "$1" in
    start)
        echo "Starting yolo26-detector..."
        start-stop-daemon -S -b -m -p $PIDFILE -x $DAEMON -- $DAEMON_ARGS >> $LOGFILE 2>&1
        ;;
    stop)
        echo "Stopping yolo26-detector..."
        start-stop-daemon -K -p $PIDFILE
        rm -f $PIDFILE
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        if [ -f $PIDFILE ] && kill -0 $(cat $PIDFILE) 2>/dev/null; then
            echo "yolo26-detector is running"
        else
            echo "yolo26-detector is not running"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
```

---

## 10. 实时预览 (`preview`)

### 概述

显示来自设备的实时视频流或数据可视化。

### 配置文件示例

```yaml
# devices/preview.yaml
version: "1.0"
id: preview
name: Live Preview
name_zh: 实时预览
type: preview

preview:
  type: mjpeg              # mjpeg | websocket | mqtt
  source: "http://{{device_ip}}:8080/stream"

  # 或 MQTT 方式
  # type: mqtt
  # broker: "mqtt://{{device_ip}}:1883"
  # topic: "recamera/detections"

user_inputs:
  - id: device_ip
    name: Device IP
    name_zh: 设备 IP
    type: text
    required: true
    placeholder: "192.168.42.1"
```

---

## 工作量估算

| 部署类型 | 配置编写 | 素材准备 | 文档编写 | 总计 |
|----------|----------|----------|----------|------|
| `esp32_usb` | 2h | 由固件开发提供 | 2h | 4h + 固件 |
| `himax_usb` | 2h | 由固件开发提供 | 2h | 4h + 固件 |
| `docker_local` | 1h | 由后端开发提供 | 1h | 2h + 镜像 |
| `docker_remote` | 2h | 由后端开发提供 | 2h | 4h + 镜像 |
| `ssh_deb` | 2h | 由后端开发提供 | 2h | 4h + deb包 |
| `script` | 2h | 由应用开发提供 | 2h | 4h + 代码 |
| `manual` | 0.5h | 截图制作 2h | 4h | 6.5h |
| `recamera_nodered` | 2h | 由 Node-RED 开发提供 | 2h | 4h + Flow |
| `recamera_cpp` | 3h | 由嵌入式开发提供 | 2h | 5h + deb包 |
| `preview` | 1h | 无 | 1h | 2h |

**说明**：以上为纯配置和文档工作量，不含素材开发时间。

---

## 协作分工建议

| 角色 | 负责内容 | 涉及部署类型 |
|------|----------|--------------|
| **方案设计** | solution.yaml、guide.md、部署流程规划 | 所有 |
| **技术文档** | Markdown 文档、截图 | 所有（尤其 manual） |
| **固件开发** | ESP32/Himax 固件、flash 配置 | esp32_usb, himax_usb |
| **后端开发** | Docker 镜像、docker-compose、deb 包 | docker_*, ssh_deb |
| **嵌入式开发** | reCamera deb 包、模型、init 脚本 | recamera_cpp |
| **Node-RED 开发** | Flow 设计与导出 | recamera_nodered |
| **测试工程师** | 端到端测试、用户输入验证 | 所有 |

---

## 相关文档

- [solution-configuration-guide.md](./solution-configuration-guide.md) - 方案配置总体指南
- [CLAUDE.md](../CLAUDE.md) - 项目总体开发指南
