# SenseCraft Solution 部署模式指南

本文档整理了系统支持的所有部署类型，包括配置方式和所需准备的文件清单，方便团队协作和工作量评估。

---

## 新建方案完整清单

新建一个方案需要准备以下文件，根据部署类型不同，所需素材有所区别。

### 通用必需文件（所有方案都需要）

```
solutions/my_solution/
├── solution.yaml                    # 【必需】方案主配置文件
├── intro/
│   ├── description.md               # 【必需】英文介绍
│   ├── description_zh.md            # 【必需】中文介绍
│   └── gallery/
│       └── cover.png/svg            # 【必需】封面图片
└── deploy/
    ├── guide.md                     # 【必需】英文部署指南
    ├── guide_zh.md                  # 【必需】中文部署指南
    └── sections/                    # 【必需】各步骤说明（每个步骤一对 md 文件）
        ├── step1.md
        └── step1_zh.md
```

### 按部署类型需要的额外素材

#### ESP32 固件烧录 (`esp32_usb`)

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

---

#### 本地 Docker 部署 (`docker_local`)

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

---

#### 远程 Docker 部署 (`docker_remote`)

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（含 SSH 配置） |
| `assets/docker/docker-compose.yml` | ✅ | 后端开发 | Docker Compose 配置 |
| `assets/docker/*` | ❌ | 后端开发 | 需要上传的其他文件 |

**需要确认的参数**：
- 目标设备架构（arm64/amd64）
- 默认 SSH 用户名
- 远程部署路径
- 是否需要自动安装 Docker

---

#### reCamera Node-RED 部署 (`recamera_nodered`)

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

---

#### reCamera C++ 应用部署 (`recamera_cpp`)

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

---

#### SSH Deb 包部署 (`ssh_deb`)

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（含 SSH 配置） |
| `assets/packages/xxx.deb` | ✅ | 后端开发 | Debian 安装包 |
| `assets/config/*` | ❌ | 后端开发 | 配置文件模板 |

**需要确认的参数**：
- 目标架构（arm64/amd64/armhf）
- systemd 服务名称
- 配置文件路径

---

#### 本地脚本部署 (`script`)

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置 |
| `assets/project/*` | ✅ | 应用开发 | 项目代码 |

**需要确认的参数**：
- 运行环境要求（Node.js/Python 版本等）
- 启动命令（Linux/macOS 和 Windows）
- 健康检查方式（日志匹配/HTTP/进程）

---

#### 手动部署 (`manual`)

| 文件 | 必需 | 来源 | 说明 |
|------|------|------|------|
| `devices/xxx.yaml` | ✅ | 配置编写 | 设备配置（最简） |
| `deploy/sections/xxx.md` | ✅ | 技术文档 | 详细操作指南 |
| `deploy/sections/xxx_zh.md` | ✅ | 技术文档 | 中文操作指南 |
| `intro/gallery/*.png` | ❌ | 技术文档 | 操作截图 |

---

### solution.yaml 模板

```yaml
version: "1.0"
id: my_solution_id                   # 方案 ID（英文，下划线分隔）
name: My Solution Name               # 英文名称
name_zh: 我的方案名称                  # 中文名称

# ============ 介绍页配置 ============
intro:
  summary: One line description
  summary_zh: 一句话描述

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md

  cover_image: intro/gallery/cover.png

  gallery:                           # 可选：更多图片
    - type: image
      src: intro/gallery/demo.png
      caption: Demo
      caption_zh: 演示

  category: sensing                  # voice_ai | sensing | automation
  tags:
    - tag1
    - tag2

  required_devices:                  # 所需硬件列表
    - name: Device Name
      name_zh: 设备名称
      image: intro/gallery/device.png
      purchase_url: https://...
      description: Device description
      description_zh: 设备描述

  stats:
    difficulty: beginner             # beginner | intermediate | advanced
    estimated_time: 30min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

# ============ 部署页配置 ============
deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md

  selection_mode: sequential         # sequential | parallel | single

  devices:                           # 部署步骤列表
    - id: step1
      name: Step 1 Name
      name_zh: 步骤1名称
      type: esp32_usb                # 部署类型
      required: true
      config_file: devices/step1.yaml
      section:
        title: Step 1 Title
        title_zh: 步骤1标题
        description_file: deploy/sections/step1.md
        description_file_zh: deploy/sections/step1_zh.md

    - id: step2
      name: Step 2 Name
      name_zh: 步骤2名称
      type: docker_remote
      required: true
      config_file: devices/step2.yaml
      section:
        title: Step 2 Title
        title_zh: 步骤2标题
        description_file: deploy/sections/step2.md
        description_file_zh: deploy/sections/step2_zh.md

  order:
    - step1
    - step2

  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps:
      - title: Access Web UI
        title_zh: 访问 Web 界面
        action: open_url
        url: "http://{{step2.host}}:8080"
```

---

### 工作量估算参考

| 部署类型 | 配置编写 | 素材准备 | 文档编写 | 总计 |
|----------|----------|----------|----------|------|
| `esp32_usb` | 2h | 由固件开发提供 | 2h | 4h + 固件 |
| `docker_local` | 1h | 由后端开发提供 | 1h | 2h + 镜像 |
| `docker_remote` | 2h | 由后端开发提供 | 2h | 4h + 镜像 |
| `recamera_nodered` | 2h | 由 Node-RED 开发提供 | 2h | 4h + Flow |
| `recamera_cpp` | 3h | 由嵌入式开发提供 | 2h | 5h + deb包 |
| `ssh_deb` | 2h | 由后端开发提供 | 2h | 4h + deb包 |
| `script` | 2h | 由应用开发提供 | 2h | 4h + 代码 |
| `manual` | 0.5h | 截图制作 2h | 4h | 6.5h |

**说明**：以上为纯配置和文档工作量，不含素材开发时间。

---

## 部署模式总览

| 类型 | 用途 | 目标平台 | 复杂度 |
|------|------|----------|--------|
| `esp32_usb` | ESP32 固件烧录 | ESP32/ESP32-S3 设备 | ⭐⭐ |
| `docker_local` | 本地 Docker 部署 | 运行 CC 的电脑 | ⭐ |
| `docker_remote` | 远程 Docker 部署 | 远程 Linux 设备（SSH） | ⭐⭐ |
| `recamera_nodered` | Node-RED Flow 部署 | reCamera 设备 | ⭐⭐ |
| `recamera_cpp` | C++ 应用部署 | reCamera 设备 | ⭐⭐⭐ |
| `ssh_deb` | deb 包安装 | 远程 Linux 设备（SSH） | ⭐⭐⭐ |
| `script` | 本地脚本执行 | 运行 CC 的电脑 | ⭐⭐ |
| `manual` | 手动操作指引 | 任何（用户自行完成） | ⭐ |

---

## 1. ESP32 USB 烧录 (`esp32_usb`)

### 概述

通过 USB 串口使用 esptool 烧录 ESP32 固件。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/firmware/*.bin` | ✅ | 固件二进制文件 |
| `deploy/sections/xxx.md` | ✅ | 烧录步骤说明文档 |

### 配置文件示例

```yaml
# devices/watcher.yaml
version: "1.0"
id: watcher
name: SenseCAP Watcher
name_zh: SenseCAP Watcher
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x10c4"      # USB Vendor ID（查设备规格）
  usb_product_id: "0xea60"     # USB Product ID
  fallback_ports:              # 备用串口匹配模式
    - "/dev/tty.usbserial-*"
    - "/dev/ttyUSB*"
    - "/dev/ttyACM*"
    - "COM*"                   # Windows

firmware:
  source:
    type: local                # local | url | github_release
    path: assets/firmware/firmware.bin
  flash_config:
    chip: esp32s3              # esp32 | esp32s3 | esp32c3
    baud_rate: 921600
    flash_mode: dio
    flash_freq: 80m
    flash_size: 16MB           # 根据实际芯片配置
    partitions:
      - name: firmware
        offset: "0x0"
        file: firmware.bin
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

### 工作量评估

- **固件开发**：需要编译生成 `.bin` 文件
- **配置编写**：需要确认芯片型号、分区表、USB ID
- **文档编写**：烧录前准备、接线说明

---

## 2. 本地 Docker 部署 (`docker_local`)

### 概述

在运行 SenseCraft 的电脑上通过 Docker Compose 启动容器服务。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/docker/docker-compose.yml` | ✅ | Docker Compose 配置 |
| `assets/docker/Dockerfile` | ❌ | 如需本地构建 |
| `assets/docker/.env.example` | ❌ | 环境变量示例 |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

### 配置文件示例

```yaml
# devices/backend.yaml
version: "1.0"
id: backend
name: Backend Services
name_zh: 后端服务
type: docker_local

detection:
  method: local
  requirements:
    - docker

docker:
  compose_file: assets/docker/docker-compose.yml

  environment:                 # 传递给 docker-compose 的环境变量
    TZ: Asia/Shanghai
    DB_USER: admin
    DB_PASSWORD: "{{db_password}}"  # 支持用户输入变量

  options:
    project_name: my-project   # docker-compose -p
    remove_orphans: true       # --remove-orphans
    build: false               # 是否需要 --build

  services:                    # 健康检查配置
    - name: api
      port: 8080
      health_check_endpoint: /health
      required: true
    - name: web
      port: 3000
      health_check_endpoint: /
      required: false          # 可选服务

user_inputs:
  - id: db_password
    name: Database Password
    name_zh: 数据库密码
    type: password
    required: true
    default: "admin123"

pre_checks:
  - type: docker
    description: Docker must be installed
  - type: port_available
    ports: [8080, 3000]
    description: Required ports must be free

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
```

### docker-compose.yml 示例

```yaml
# assets/docker/docker-compose.yml
version: '3.8'

services:
  api:
    image: myregistry/my-api:latest
    ports:
      - "8080:8080"
    environment:
      - TZ=${TZ:-Asia/Shanghai}
      - DB_PASSWORD=${DB_PASSWORD}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  web:
    image: myregistry/my-web:latest
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  data:
```

### 工作量评估

- **镜像开发**：构建并推送 Docker 镜像到仓库
- **Compose 编写**：服务编排、端口映射、健康检查
- **配置编写**：环境变量、用户输入
- **文档编写**：前置要求、部署后访问方式

---

## 3. 远程 Docker 部署 (`docker_remote`)

### 概述

通过 SSH 连接到远程 Linux 设备，上传 docker-compose 文件并启动容器。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/docker/docker-compose.yml` | ✅ | Docker Compose 配置 |
| `assets/docker/*` | ❌ | 其他需要上传的文件 |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

### 配置文件示例

```yaml
# devices/edge_device.yaml
version: "1.0"
id: edge_device
name: Edge Device
name_zh: 边缘设备
type: docker_remote

detection:
  method: network_scan
  manual_entry: true           # 允许手动输入 IP

ssh:
  port: 22
  default_user: ubuntu
  auth_methods:
    - password
    - key
  connection_timeout: 30
  command_timeout: 600         # 拉取镜像可能较慢

docker_remote:
  compose_file: assets/docker/docker-compose.yml
  compose_dir: assets/docker   # 上传整个目录（包含子文件）

  remote_path: /home/{{username}}/myapp  # 远程部署路径，支持变量

  environment:
    TZ: Asia/Shanghai
    DEVICE_NAME: "{{device_name}}"
    API_KEY: "{{api_key}}"

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
      message: Please enter a valid IP address

  - id: username
    name: SSH Username
    name_zh: SSH 用户名
    type: text
    default: ubuntu
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

  - id: api_key
    name: API Key
    name_zh: API 密钥
    type: password
    required: false

  - id: auto_install_docker
    name: Auto Install Docker
    name_zh: 自动安装 Docker
    type: checkbox
    default: "true"
    description: Automatically install Docker if not present
    description_zh: 如果设备未安装 Docker，自动安装

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

### 工作量评估

- **镜像开发**：同 docker_local
- **Compose 编写**：需考虑 ARM/x86 架构兼容性
- **配置编写**：SSH 配置、用户输入、变量替换
- **文档编写**：设备准备、网络配置、故障排查

---

## 4. SSH Deb 包部署 (`ssh_deb`)

### 概述

通过 SSH 连接到远程 Linux 设备，上传并安装 .deb 包，配置 systemd 服务。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/packages/xxx.deb` | ✅ | Debian 安装包 |
| `assets/config/*` | ❌ | 配置文件（如需要） |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

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
    type: local                # local | url
    path: assets/packages/myapp_1.0.0_arm64.deb
    # 或从 URL 下载：
    # type: url
    # url: https://releases.example.com/myapp_1.0.0_arm64.deb
    checksum:                  # 可选：校验和验证
      sha256: "abc123..."

  install_commands:            # 自定义安装命令（可选）
    - "dpkg -i {package}"
    - "apt-get install -f -y"  # 自动安装依赖

  config_files:                # 配置文件部署
    - source: assets/config/app.yaml
      destination: /etc/myapp/config.yaml
      mode: "0644"
    - source: assets/config/credentials.json
      destination: /etc/myapp/credentials.json
      mode: "0600"

  service:                     # systemd 服务配置
    name: myapp
    enable: true               # systemctl enable
    start: true                # systemctl start

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

### 工作量评估

- **打包开发**：构建 .deb 包（包含二进制、依赖、systemd unit）
- **配置文件**：准备默认配置文件模板
- **配置编写**：安装命令、服务配置
- **文档编写**：系统要求、架构兼容性（arm64/amd64）

---

## 5. 本地脚本部署 (`script`)

### 概述

在本地执行脚本命令，支持配置文件生成和健康检查。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/project/*` | ✅ | 项目代码/脚本 |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

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
  working_dir: assets/mcp_bridge  # 工作目录（相对于方案目录）

  setup_commands:              # 前置命令（按顺序执行）
    - command: "npm install"
      description: "Install dependencies"
    - command: "npm run build"
      description: "Build project"

  config_template:             # 配置文件生成（支持变量替换）
    file: .env
    content: |
      API_KEY={{api_key}}
      SERVER_URL={{server_url}}
      DEBUG={{debug_mode}}

  start_command:               # 启动命令（平台特定）
    linux_macos: "npm start"
    windows: "npm.cmd start"
    env:                       # 额外环境变量
      NODE_ENV: production
      PORT: "3000"

  health_check:
    type: log_pattern          # log_pattern | http | process
    pattern: "Server listening on port"  # 正则匹配
    timeout_seconds: 30
    # 或 HTTP 检查：
    # type: http
    # url: http://localhost:3000/health
    # timeout_seconds: 30

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

### 工作量评估

- **项目开发**：可执行的脚本/程序
- **配置模板**：环境变量、配置文件模板
- **配置编写**：启动命令、健康检查方式
- **文档编写**：环境要求（Node.js、Python 等）

---

## 6. 手动部署 (`manual`)

### 概述

仅显示操作指南，用户手动完成配置。适用于无法自动化的步骤。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件（最简） |
| `deploy/sections/xxx.md` | ✅ | 详细操作指南 |
| `deploy/sections/xxx_zh.md` | ✅ | 中文操作指南 |
| `intro/gallery/*.png` | ❌ | 截图/示意图 |

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
# 主要靠 solution.yaml 中的 section 描述

steps:
  - id: manual_steps
    name: Follow Instructions
    name_zh: 按照指引操作
```

### Markdown 指南示例

```markdown
<!-- deploy/sections/grafana.md -->
## Configure Grafana Dashboard

### Step 1: Login to Grafana

1. Open browser and navigate to `http://localhost:3000`
2. Login with default credentials:
   - Username: `admin`
   - Password: `admin`
3. Change password when prompted

### Step 2: Add Data Source

1. Click **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **InfluxDB**
4. Configure connection:
   - URL: `http://influxdb:8086`
   - Organization: `seeed`
   - Token: *(copy from InfluxDB)*

![Data Source Config](../intro/gallery/grafana-datasource.png)

### Step 3: Import Dashboard

1. Click **+** → **Import**
2. Upload the dashboard JSON file from the solution package
3. Select the InfluxDB data source
4. Click **Import**
```

### 工作量评估

- **文档编写**：详细的分步骤操作指南
- **截图制作**：关键步骤的界面截图
- **双语支持**：英文和中文版本

---

## 7. reCamera Node-RED 部署 (`recamera_nodered`)

### 概述

通过 Node-RED Admin HTTP API 部署 Flow 到 reCamera 设备。自动处理冲突服务和配置更新。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/nodered/flow.json` | ✅ | Node-RED Flow 文件 |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

### 配置文件示例

```yaml
# devices/recamera.yaml
version: "1.0"
id: recamera
name: reCamera Node-RED
name_zh: reCamera Node-RED 配置
type: recamera_nodered

detection:
  method: network_scan
  manual_entry: true

nodered:
  flow_file: assets/nodered/flow.json  # Flow 模板文件
  port: 1880                           # Node-RED 端口
  influxdb_node_id: "069087e0ad1b172e" # InfluxDB 节点 ID（自动配置）

user_inputs:
  - id: recamera_ip
    name: reCamera IP
    name_zh: reCamera IP 地址
    type: text
    required: true
    placeholder: "192.168.42.1"
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

  # 可选：SSH 凭据用于停止冲突的 C++ 服务
  - id: ssh_password
    name: SSH Password (Optional)
    name_zh: SSH 密码（可选）
    type: password
    required: false
    description: Required to stop conflicting C++ services
    description_zh: 用于停止冲突的 C++ 服务

  # 可选：InfluxDB 配置（自动注入到 Flow）
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

### 工作量评估

- **Flow 开发**：在 Node-RED 中设计并导出 Flow
- **配置编写**：用户输入、InfluxDB 节点 ID
- **文档编写**：reCamera 网络配置、Flow 功能说明

---

## 8. reCamera C++ 应用部署 (`recamera_cpp`)

### 概述

通过 SSH + opkg 部署 C++ 应用到 reCamera 设备。支持 deb 包安装、模型文件部署、SysVinit 服务配置。

### 需要提供的文件

| 文件 | 必需 | 说明 |
|------|------|------|
| `devices/xxx.yaml` | ✅ | 设备配置文件 |
| `assets/packages/xxx.deb` | ✅ | opkg 安装包 |
| `assets/models/*.cvimodel` | ❌ | AI 模型文件 |
| `assets/scripts/init_script` | ❌ | SysVinit 脚本（如 deb 不包含） |
| `deploy/sections/xxx.md` | ✅ | 部署说明文档 |

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
  # Deb 包配置
  deb_package:
    path: assets/packages/yolo26-detector_1.0.0_riscv64.deb
    name: yolo26-detector        # 包名（用于 opkg remove）
    includes_init_script: true   # deb 是否已包含启动脚本

  # 模型文件配置
  models:
    - path: assets/models/yolo26.cvimodel
      target_path: /userdata/local/models
      filename: yolo26.cvimodel  # 目标文件名（可选）
    - path: assets/models/config.json
      target_path: /userdata/local/models

  # Init 脚本配置（仅当 deb 不包含时需要）
  init_script:
    name: yolo26-detector        # 服务名
    priority: 92                 # SysVinit 优先级 → S92yolo26-detector
    path: assets/scripts/init_script  # 自定义脚本路径（可选）
    binary_path: /usr/local/bin  # 二进制安装路径
    daemon_args: "--config /etc/yolo26/config.json"
    log_file: /var/log/yolo26.log
    ld_library_path: "/mnt/system/lib:/mnt/system/usr/lib"

  # MQTT 外部访问配置（可选）
  mqtt_config:
    enable: true
    port: 1883
    allow_anonymous: true

  # 冲突服务处理
  conflict_services:
    stop:                        # 部署前停止的服务
      - S03node-red
      - S91sscma-node
      - S93sscma-supervisor
    disable:                     # 需要禁用的服务（S→K 重命名）
      - node-red
      - sscma-node

  auto_start: true               # 部署后自动启动
  service_name: yolo26-detector  # 向后兼容
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

### 工作量评估

- **应用开发**：C++ 程序编译（RISC-V 交叉编译）
- **打包开发**：制作 opkg/deb 安装包
- **模型准备**：AI 模型转换为 .cvimodel 格式
- **脚本开发**：SysVinit 启动脚本（如需要）
- **配置编写**：冲突服务、MQTT 配置
- **文档编写**：模型说明、性能参数

---

## 目录结构汇总

```
solutions/
└── my_solution/
    ├── solution.yaml              # 方案主配置
    │
    ├── intro/                     # 介绍页内容
    │   ├── description.md
    │   ├── description_zh.md
    │   └── gallery/
    │       ├── cover.png
    │       └── architecture.svg
    │
    ├── deploy/                    # 部署页内容
    │   ├── guide.md
    │   ├── guide_zh.md
    │   ├── success.md
    │   ├── success_zh.md
    │   └── sections/              # 各步骤说明
    │       ├── step1.md
    │       ├── step1_zh.md
    │       └── ...
    │
    ├── devices/                   # 设备配置
    │   ├── step1.yaml             # esp32_usb 配置
    │   ├── step2.yaml             # docker_remote 配置
    │   └── ...
    │
    └── assets/                    # 部署资源
        ├── docker/
        │   ├── docker-compose.yml
        │   └── Dockerfile
        ├── firmware/
        │   └── firmware.bin
        ├── packages/
        │   └── myapp.deb
        ├── models/
        │   └── model.cvimodel
        ├── nodered/
        │   └── flow.json
        ├── config/
        │   └── app.yaml
        └── scripts/
            └── init_script
```

---

## 协作分工建议

| 角色 | 负责内容 | 涉及部署类型 |
|------|----------|--------------|
| **方案设计** | solution.yaml、部署流程规划 | 所有 |
| **技术文档** | Markdown 文档、截图 | 所有（尤其 manual） |
| **固件开发** | ESP32 固件、flash 配置 | esp32_usb |
| **后端开发** | Docker 镜像、docker-compose | docker_local, docker_remote |
| **嵌入式开发** | deb 包、模型、init 脚本 | ssh_deb, recamera_cpp |
| **Node-RED 开发** | Flow 设计与导出 | recamera_nodered |
| **测试工程师** | 端到端测试、用户输入验证 | 所有 |

---

## 快速开始模板

根据目标平台选择对应的模板：

| 目标 | 推荐类型 | 复杂度 |
|------|----------|--------|
| 烧录 ESP32 固件 | `esp32_usb` | ⭐⭐ |
| 本机运行 Docker 服务 | `docker_local` | ⭐ |
| 远程设备运行 Docker | `docker_remote` | ⭐⭐ |
| 远程安装 Linux 软件包 | `ssh_deb` | ⭐⭐⭐ |
| 本地运行脚本/程序 | `script` | ⭐⭐ |
| 配置 reCamera Node-RED | `recamera_nodered` | ⭐⭐ |
| 部署 reCamera C++ 应用 | `recamera_cpp` | ⭐⭐⭐ |
| 需要用户手动操作 | `manual` | ⭐ |
