# SenseCraft Solution 配置指南

本文档详细说明如何配置 IoT 解决方案，特别是如何使用 **Preset（预设套餐）** 模式来支持不同规模和场景的部署方案。

---

## 目录

1. [目录结构](#目录结构)
2. [solution.yaml 配置详解](#solutionyaml-配置详解)
   - [基础信息](#基础信息)
   - [设备目录 (device_catalog)](#设备目录-device_catalog)
   - [设备组 (device_groups)](#设备组-device_groups)
   - [预设套餐 (presets)](#预设套餐-presets)
   - [Preset 专属部署设备 (preset.devices)](#preset-专属部署设备-presetdevices)
   - [部署配置 (deployment)](#部署配置-deployment)
3. [设备配置文件](#设备配置文件)
4. [完整示例](#完整示例)
5. [最佳实践](#最佳实践)

---

## 目录结构

```
solutions/
└── your_solution_id/
    ├── solution.yaml           # 主配置文件
    ├── intro/                   # 介绍页内容
    │   ├── description.md       # 英文介绍
    │   ├── description_zh.md    # 中文介绍
    │   └── gallery/             # 图片资源
    │       ├── cover.png        # 封面图
    │       ├── architecture.png # 架构图
    │       └── ...
    ├── deploy/                  # 部署页内容
    │   ├── guide.md             # 部署指南（英文）
    │   ├── guide_zh.md          # 部署指南（中文）
    │   └── sections/            # 各步骤说明
    │       ├── step1.md
    │       ├── step1_zh.md
    │       ├── step1_troubleshoot.md
    │       └── ...
    └── devices/                 # 设备配置
        ├── device1.yaml
        └── device2.yaml
```

---

## solution.yaml 配置详解

### 基础信息

```yaml
version: "1.0"
id: indoor_positioning_ble_lorawan    # 唯一标识符（英文小写+下划线）
name: Indoor Positioning System       # 英文名称
name_zh: 室内定位系统                   # 中文名称
```

---

### 设备目录 (device_catalog)

定义方案中涉及的所有硬件设备。这是一个 **字典结构**，key 为设备引用 ID。

```yaml
intro:
  device_catalog:
    # 基础定义：key 是设备引用 ID
    t1000_tracker:
      name: SenseCAP T1000 Tracker
      name_zh: SenseCAP T1000 追踪器
      image: intro/gallery/t1000.png
      product_url: https://www.seeedstudio.com/...
      description: LoRaWAN tracker with BLE scanning
      description_zh: 支持 BLE 扫描的 LoRaWAN 追踪器

    bc01_beacon:
      name: BC01 BLE Beacon
      name_zh: BC01 蓝牙信标
      image: intro/gallery/beacon.png
      product_url: https://www.seeedstudio.com/...

    # 同类设备的不同版本（如不同频段）
    gateway_us915:
      name: SenseCAP M2 Gateway (US915)
      name_zh: SenseCAP M2 网关 (US915)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...-US915-...
      description: LoRaWAN gateway for Americas (US915)
      description_zh: 美洲地区网关 (US915)

    gateway_eu868:
      name: SenseCAP M2 Gateway (EU868)
      name_zh: SenseCAP M2 网关 (EU868)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...-EU868-...
      description: LoRaWAN gateway for Europe (EU868)
      description_zh: 欧洲地区网关 (EU868)

    gateway_as923:
      name: SenseCAP M2 Gateway (AS923)
      name_zh: SenseCAP M2 网关 (AS923)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...-AS923-...
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 设备英文名称 |
| `name_zh` | string | 否 | 设备中文名称 |
| `image` | string | 否 | 设备图片路径 |
| `product_url` | string | 否 | 购买链接 |
| `wiki_url` | string | 否 | Wiki 文档链接 |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `category` | string | 否 | 设备类别 |

---

### 设备组 (device_groups)

定义用户在介绍页可以选择的设备组合。支持三种类型：

#### 1. single 类型 - 单选

用于同类设备中只能选择一个的情况（如选择地区对应的网关）。

```yaml
  device_groups:
    - id: gateway                    # 组 ID，用于 preset 引用
      name: LoRaWAN Gateway
      name_zh: LoRaWAN 网关
      type: single                   # 单选类型
      required: true
      description: Select the gateway for your region
      description_zh: 选择您所在地区的网关
      options:
        - device_ref: gateway_us915  # 引用 device_catalog 中的 key
          label: Americas (US915)
          label_zh: 美洲 (US915)
        - device_ref: gateway_eu868
          label: Europe (EU868)
          label_zh: 欧洲 (EU868)
        - device_ref: gateway_as923
          label: Asia-Pacific (AS923)
          label_zh: 亚太 (AS923)
      default: gateway_us915         # 默认选中项
```

#### 2. quantity 类型 - 数量选择

用于需要指定数量的设备。

```yaml
    - id: beacons
      name: BLE Beacons
      name_zh: BLE 信标
      type: quantity                 # 数量类型
      required: true
      device_ref: bc01_beacon        # 引用单个设备
      min_count: 3                   # 最小数量
      max_count: 100                 # 最大数量
      default_count: 6               # 默认数量
      description: "Recommended: 3-5 per zone"
      description_zh: "建议：每个区域 3-5 个"
```

#### 3. multiple 类型 - 多选

用于可以选择多个不同设备的情况。

```yaml
    - id: sensors
      name: Additional Sensors
      name_zh: 附加传感器
      type: multiple                 # 多选类型
      required: false
      min_count: 0
      max_count: 5
      options:
        - device_ref: temp_sensor
          label: Temperature Sensor
        - device_ref: humidity_sensor
          label: Humidity Sensor
      default_selections:            # 默认选中的项
        - temp_sensor
```

---

### 预设套餐 (presets)

**这是核心功能**：定义不同规模/场景的部署方案，用户可以一键选择。

每个 preset 包含：
- **device_groups**：该套餐需要的设备选择（显示在介绍页）
- **devices**：该套餐的完整部署步骤（显示在部署页）

```yaml
  presets:
    # ========== 入门套件 ==========
    - id: starter
      name: Starter Kit
      name_zh: 入门套件
      description: Small office (up to 500 sqm)
      description_zh: 小型办公室（500平方米以内）
      badge: Popular                 # 角标（显示在套餐卡片上）
      badge_zh: 热门
      device_groups:                 # 设备组（介绍页选择）
        - id: gateway
          name: LoRaWAN Gateway
          type: single
          options:
            - device_ref: gateway_us915
          default: gateway_us915
        - id: beacons
          name: BLE Beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 6
      architecture_image: intro/gallery/starter_arch.png  # 架构图
      links:
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...
      section:                       # 该套餐的部署指南
        title: Starter Kit Deployment
        title_zh: 入门套件部署指南
        description_file: deploy/sections/starter_guide.md
        description_file_zh: deploy/sections/starter_guide_zh.md
      devices:                       # 该套餐的部署步骤
        - id: beacons
          name: Deploy BLE Beacons
          name_zh: 部署 BLE 信标
          type: manual
          # ... 完整设备配置 ...
        - id: app_server
          name: Deploy Application
          type: docker_deploy
          # ... 完整设备配置 ...

    # ========== 标准配置 ==========
    - id: standard
      name: Standard Setup
      name_zh: 标准配置
      description: Medium facility (500-2000 sqm)
      description_zh: 中型设施（500-2000平方米）
      device_groups:
        - id: gateway
          type: single
          options:
            - device_ref: gateway_us915
          default: gateway_us915
        - id: beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 15
      links:
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...
      devices:
        # ... 该套餐的部署步骤 ...

    # ========== 企业版 ==========
    - id: enterprise
      name: Enterprise
      name_zh: 企业版
      description: Large facility (2000+ sqm)
      description_zh: 大型设施（2000平方米以上）
      device_groups:
        - id: beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 30
      links:
        wiki: https://wiki.seeedstudio.com/...
      devices:
        # ... 该套餐的部署步骤 ...
```

**Preset 字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 套餐唯一标识 |
| `name` / `name_zh` | string | 是 | 套餐名称 |
| `description` / `description_zh` | string | 否 | 套餐描述 |
| `badge` / `badge_zh` | string | 否 | 角标文字（如"热门"、"推荐"） |
| `device_groups` | list | 否 | 设备组定义，用于介绍页的设备选择 |
| `architecture_image` | string | 否 | 该套餐的架构图 |
| `links` | object | 否 | 相关链接（wiki、github） |
| `section` | object | 否 | 套餐专属的部署指南 |
| `devices` | list | **是** | 该套餐的完整部署步骤列表 |

---

### Preset 专属部署设备 (preset.devices)

**重要变更**：从 v1.1 开始，每个 preset 包含自己独立的 `devices` 列表，定义该套餐的完整部署流程。

#### 为什么这样设计？

旧方式（已废弃）：
```yaml
# ❌ 旧方式：使用 show_when 条件过滤全局设备列表
deployment:
  devices:
    - id: step1
      show_when:
        preset: preset_a    # 仅在 preset_a 时显示
    - id: step2
      show_when:
        preset: [preset_a, preset_b]  # 在两个 preset 时显示
```

新方式（推荐）：
```yaml
# ✅ 新方式：每个 preset 有完整的设备列表
intro:
  presets:
    - id: preset_a
      devices:
        - id: step1
          name: Step 1
          type: manual
          # ... 完整配置
        - id: step2
          name: Step 2
          type: docker_deploy
          # ... 完整配置

    - id: preset_b
      devices:
        - id: step2
          name: Step 2
          type: docker_deploy
          # ... 完整配置
        - id: step3
          name: Step 3
          type: esp32_usb
          # ... 完整配置

deployment:
  devices: []   # 留空，设备定义已移至各 preset
  order: []     # 留空，顺序由 preset.devices 数组顺序决定
```

#### 优势

1. **更清晰**：一眼看出每个套餐包含哪些部署步骤
2. **更灵活**：不同套餐可以有完全不同的步骤顺序
3. **无歧义**：不需要理解复杂的 show_when 条件逻辑
4. **易维护**：修改一个套餐不会影响其他套餐

#### preset.devices 设备字段

每个 preset 中的设备支持以下类型和字段：

```yaml
devices:
  - id: unique_step_id           # 步骤唯一标识
    name: Step Name              # 英文名称
    name_zh: 步骤名称             # 中文名称
    type: manual                 # 类型：manual | esp32_usb | docker_deploy | preview
    required: true               # 是否必须完成
    config_file: devices/xxx.yaml  # 设备配置文件（部分类型需要）
    section:                     # 步骤说明
      title: Step Title
      title_zh: 步骤标题
      description_file: deploy/sections/step.md
      description_file_zh: deploy/sections/step_zh.md
      troubleshoot_file: deploy/sections/step_troubleshoot.md
      wiring:
        image: intro/gallery/wiring.png
        steps: [...]
        steps_zh: [...]
    targets:                     # 多目标部署（可选）
      local:
        name: Local Deployment
        default: true
        config_file: devices/local.yaml
        section: {...}
      remote:
        name: Remote Deployment
        config_file: devices/remote.yaml
        section: {...}
```

---

### 部署配置 (deployment)

#### 基础结构

> **注意**：从 v1.1 开始，部署设备定义已移至各 `preset.devices` 中。
> `deployment.devices` 和 `deployment.order` 保留为空数组以保持向后兼容。

```yaml
deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  selection_mode: sequential         # sequential | single_choice

  # 设备列表已移至各 preset.devices 中
  devices: []

  # 顺序由各 preset.devices 数组顺序决定
  order: []

  post_deployment:                   # 部署后操作
    success_message_file: deploy/success.md
    next_steps:
      - title: Access Dashboard
        action: open_url
        url: http://localhost:5173
```

#### 部署步骤类型

##### 1. manual - 手动操作步骤

```yaml
  devices:
    - id: beacons
      name: Deploy BLE Beacons
      name_zh: 部署 BLE 信标
      type: manual
      required: true
      section:
        title: Step 1 - Deploy BLE Beacons
        title_zh: 第一步 - 部署 BLE 信标
        description_file: deploy/sections/beacons.md
        description_file_zh: deploy/sections/beacons_zh.md
        troubleshoot_file: deploy/sections/beacons_troubleshoot.md
        wiring:
          steps:
            - Place beacons at strategic locations
            - Record MAC address of each beacon
          steps_zh:
            - 在关键位置放置信标
            - 记录每个信标的 MAC 地址
```

##### 2. esp32_usb - ESP32 固件烧录

```yaml
    - id: watcher_esp32
      name: Flash Xiaozhi Firmware
      name_zh: 烧录小智固件
      type: esp32_usb
      required: true
      config_file: devices/watcher_esp32.yaml    # 引用设备配置文件
      section:
        title: Step 1 - Flash Firmware
        title_zh: 第一步 - 烧录固件
        description_file: deploy/sections/flash_esp32.md
        troubleshoot_file: deploy/sections/flash_esp32_troubleshoot.md
        wiring:
          steps:
            - Connect device via USB-C
            - Select the serial port
            - Click Flash button
          steps_zh:
            - 通过 USB-C 连接设备
            - 选择串口
            - 点击烧录按钮
```

##### 3. docker_deploy - Docker 部署（支持多目标）

```yaml
    - id: app_server
      name: Deploy Application
      name_zh: 部署应用程序
      type: docker_deploy
      required: true
      config_file: devices/app_local.yaml
      section:
        title: Step 2 - Deploy Application
        title_zh: 第二步 - 部署应用程序
      targets:                       # 多个部署目标
        local:
          name: Local Deployment
          name_zh: 本机部署
          description: Deploy on this computer
          description_zh: 部署到当前电脑
          default: true
          config_file: devices/app_local.yaml
          section:
            description_file: deploy/sections/app_local.md
            troubleshoot_file: deploy/sections/app_local_troubleshoot.md
        remote:
          name: Remote Deployment
          name_zh: 远程部署
          description: Deploy via SSH
          description_zh: 通过 SSH 部署
          config_file: devices/app_remote.yaml
          section:
            description_file: deploy/sections/app_remote.md
```

##### 4. preview - 实时预览

```yaml
    - id: preview
      name: Live Preview
      name_zh: 实时预览
      type: preview
      required: false
      config_file: devices/preview.yaml
      section:
        title: Real-time Preview
        title_zh: 实时预览
        description_file: deploy/sections/preview.md
```

#### 条件显示 (show_when) - 已废弃

> **已废弃**：从 v1.1 开始，不再使用 `show_when.preset` 条件。
> 请改用 `preset.devices` 方式，将设备直接定义在各自的 preset 中。

```yaml
# ❌ 旧方式（已废弃）
deployment:
  devices:
    - id: face_esp32
      show_when:
        preset: face_recognition
      ...

# ✅ 新方式
intro:
  presets:
    - id: face_recognition
      devices:
        - id: face_esp32
          ...
```

---

## 设备配置文件

设备配置文件放在 `devices/` 目录下，定义具体的部署参数。

### Docker 本地部署配置

```yaml
# devices/app_local.yaml
version: "1.0"
id: app_local
name: Application (Local)
name_zh: 应用程序（本机）
type: docker_local

detection:
  method: local
  requirements:
    - docker_installed
    - docker_running

docker:
  image: seeedcloud/your-app
  container_name: your-app
  ports:
    - "5173:5173"
  volumes:
    - ./db:/app/db/
    - ./config:/app/config
  restart: unless-stopped

  services:
    - name: your-app
      port: 5173
      health_check_endpoint: /
      required: true

  images:
    - name: seeedcloud/your-app
      required: true

pre_checks:
  - type: docker_version
    min_version: "20.0"
    description: Check Docker version

steps:
  - id: pull_images
    name: Pull Docker Images
    name_zh: 拉取 Docker 镜像
    optional: false
    default: true

  - id: start_services
    name: Start Services
    name_zh: 启动服务
    optional: false
    default: true

  - id: health_check
    name: Health Check
    name_zh: 健康检查
    optional: false
    default: true

post_deployment:
  open_browser: true
  url: "http://localhost:5173"
  credentials:
    username: admin
    password: your-password
```

### ESP32 固件烧录配置

```yaml
# devices/watcher_esp32.yaml
version: "1.0"
id: watcher_esp32
name: ESP32 Firmware
name_zh: ESP32 固件
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"
  fallback_ports:
    - "/dev/tty.wchusbserial*"
    - "/dev/cu.wchusbserial*"
    - "/dev/ttyUSB*"

firmware:
  source:
    type: local
    path: assets/firmware/merged-binary.bin
  flash_config:
    chip: esp32s3
    baud_rate: 921600
    flash_mode: dio
    flash_freq: 80m
    flash_size: 16MB
    partitions:
      - name: merged_firmware
        offset: "0x0"
        file: merged-binary.bin

user_inputs:
  - id: serial_port
    name: Serial Port
    name_zh: 串口
    type: serial_port
    required: true
    auto_detect: true

pre_checks:
  - type: serial_port_available
  - type: esptool_available

steps:
  - id: detect_chip
    name: Detect Chip
    name_zh: 检测芯片
  - id: flash_firmware
    name: Flash Firmware
    name_zh: 烧录固件
  - id: reset_device
    name: Reset Device
    name_zh: 重启设备

post_deployment:
  reset_device: true
  wait_for_ready: 3
```

### 预览配置

```yaml
# devices/preview.yaml
version: "1.0"
id: preview_heatmap
name: Heatmap Preview
name_zh: 热力图预览
type: preview

video:
  type: rtsp_proxy
  rtsp_url_template: "{{rtsp_url}}"

mqtt:
  broker_template: "{{mqtt_broker}}"
  port_template: "{{mqtt_port}}"
  topic_template: "{{mqtt_topic}}"

overlay:
  renderer: custom
  script_file: preview/draw_heatmap.js

display:
  aspect_ratio: "16:9"
  auto_start: false
  show_stats: true

user_inputs:
  - id: rtsp_url
    name: RTSP URL
    name_zh: RTSP 地址
    type: text
    required: true
    default: "rtsp://192.168.42.1:8554/live0"

  - id: mqtt_broker
    name: MQTT Broker
    name_zh: MQTT 服务器
    type: text
    required: true
    default: "192.168.42.1"
```

---

## 完整示例

### 示例 1：多套餐室内定位方案

```yaml
version: "1.0"
id: indoor_positioning_ble_lorawan
name: Indoor Positioning with BLE & LoRaWAN
name_zh: 蓝牙 LoRaWAN 室内定位系统

intro:
  summary: Indoor positioning system combining BLE beacons and LoRaWAN
  summary_zh: 结合 BLE 信标和 LoRaWAN 的室内定位系统

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md
  cover_image: intro/gallery/cover.png

  category: smart_building
  tags: [iot, lorawan, bluetooth, indoor-positioning]

  # ========== 设备目录 ==========
  device_catalog:
    t1000_tracker:
      name: SenseCAP T1000 Tracker
      name_zh: SenseCAP T1000 追踪器
      image: intro/gallery/t1000.png
      product_url: https://www.seeedstudio.com/...

    bc01_beacon:
      name: BC01 BLE Beacon
      name_zh: BC01 蓝牙信标
      image: intro/gallery/beacon.png
      product_url: https://www.seeedstudio.com/...

    gateway_us915:
      name: SenseCAP M2 Gateway (US915)
      name_zh: SenseCAP M2 网关 (US915)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...

  # ========== 预设套餐（每个 preset 包含完整的 devices 列表） ==========
  presets:
    - id: starter
      name: Starter Kit
      name_zh: 入门套件
      description: Small office (up to 500 sqm)
      description_zh: 小型办公室（500平方米以内）
      badge: Popular
      badge_zh: 热门
      device_groups:
        - id: gateway
          name: LoRaWAN Gateway
          type: single
          options:
            - device_ref: gateway_us915
          default: gateway_us915
        - id: beacons
          name: BLE Beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 6
      links:
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...
      # 该套餐的完整部署步骤
      devices:
        - id: beacons
          name: Deploy BLE Beacons
          name_zh: 部署 BLE 信标
          type: manual
          required: true
          section:
            title: Step 1 - Deploy BLE Beacons
            title_zh: 第一步 - 部署 BLE 信标
            description_file: deploy/sections/beacons.md
            description_file_zh: deploy/sections/beacons_zh.md
        - id: gateway
          name: Setup LoRaWAN Gateway
          name_zh: 设置 LoRaWAN 网关
          type: manual
          required: true
          section:
            title: Step 2 - Setup Gateway
            title_zh: 第二步 - 设置网关
            description_file: deploy/sections/gateway.md
            description_file_zh: deploy/sections/gateway_zh.md
        - id: app_server
          name: Deploy Application
          name_zh: 部署应用程序
          type: docker_deploy
          required: true
          config_file: devices/app_local.yaml
          section:
            title: Step 3 - Deploy Application
            title_zh: 第三步 - 部署应用程序
          targets:
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/app_local.yaml
              section:
                description_file: deploy/sections/app_local.md
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/app_remote.yaml
              section:
                description_file: deploy/sections/app_remote.md
        - id: tracker
          name: Configure Tracker
          name_zh: 配置追踪器
          type: manual
          required: true
          section:
            title: Step 4 - Configure Tracker
            title_zh: 第四步 - 配置追踪器
            description_file: deploy/sections/tracker.md
            description_file_zh: deploy/sections/tracker_zh.md

    - id: standard
      name: Standard Setup
      name_zh: 标准配置
      description: Medium facility (500-2000 sqm)
      description_zh: 中型设施（500-2000平方米）
      device_groups:
        - id: beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 15
      links:
        wiki: https://wiki.seeedstudio.com/...
      devices:
        # 与 starter 相同的步骤，但可以有不同的配置
        - id: beacons
          # ... 同上
        - id: gateway
          # ... 同上
        - id: app_server
          # ... 同上
        - id: tracker
          # ... 同上

    - id: enterprise
      name: Enterprise
      name_zh: 企业版
      description: Large facility (2000+ sqm)
      description_zh: 大型设施（2000平方米以上）
      device_groups:
        - id: beacons
          type: quantity
          device_ref: bc01_beacon
          default_count: 30
      links:
        wiki: https://wiki.seeedstudio.com/...
      devices:
        # 企业版可能有额外的步骤
        - id: beacons
          # ... 同上
        - id: gateway
          # ... 同上
        - id: app_server
          # ... 同上
        - id: tracker
          # ... 同上

  stats:
    difficulty: intermediate
    estimated_time: 60min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

# ========== 部署配置（设备已移至 preset.devices） ==========
deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  selection_mode: sequential

  # 设备列表已移至各 preset.devices 中
  devices: []
  order: []

  post_deployment:
    success_message_file: deploy/success.md
    next_steps:
      - title: Access Dashboard
        title_zh: 访问仪表板
        action: open_url
        url: http://localhost:5173
```

### 示例 2：多功能组合方案（每个 preset 有不同的部署步骤）

```yaml
version: "1.0"
id: smart_space_assistant
name: Smart Space AI Assistant
name_zh: 打造空间 AI 智能体

intro:
  summary: Upgrade Xiaozhi with face recognition and display casting
  summary_zh: 让小智认识你的脸、把对话投到大屏

  device_catalog:
    sensecap_watcher:
      image: intro/gallery/watcher.svg
    recomputer_r1000:
      image: intro/gallery/recomputer.svg
    hdmi_display: {}

  # ========== 两种功能作为独立的 preset ==========
  presets:
    # ===== 人脸识别功能 =====
    - id: face_recognition
      name: Face Recognition
      name_zh: 人脸识别
      badge: Recommended
      badge_zh: 推荐
      description: Add face recognition to Xiaozhi
      description_zh: 给小智装上"眼睛"
      device_groups:
        - id: voice_assistant
          name: Voice Assistant Device
          type: single
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher
      architecture_image: intro/gallery/demo.svg
      # 人脸识别功能的部署步骤
      devices:
        - id: face_esp32
          name: Flash Xiaozhi Firmware
          name_zh: 烧录小智固件
          type: esp32_usb
          required: true
          config_file: devices/watcher_esp32.yaml
          section:
            title: "Step 1: Flash Xiaozhi Firmware"
            title_zh: "第一步：烧录小智固件"
            description_file: deploy/sections/flash_esp32.md
        - id: face_himax
          name: Flash Face Recognition Firmware
          name_zh: 烧录人脸识别固件
          type: himax_usb
          required: true
          config_file: devices/watcher_himax.yaml
          section:
            title: "Step 2: Flash Face Recognition"
            title_zh: "第二步：烧录人脸识别固件"
            description_file: deploy/sections/flash_himax.md
        - id: face_configure
          name: Configure Xiaozhi
          name_zh: 配置小智
          type: manual
          required: true
          section:
            title: "Step 3: Configure Xiaozhi"
            title_zh: "第三步：配置小智"
            description_file: deploy/sections/configure_xiaozhi.md
        - id: face_enrollment
          name: Face Enrollment
          name_zh: 人脸录入
          type: manual
          required: false
          section:
            title: "Step 4: Enroll Faces"
            title_zh: "第四步：录入人脸"
            description_file: deploy/sections/face_enrollment.md

    # ===== 投屏功能 =====
    - id: display_cast
      name: Display Cast
      name_zh: 大屏投屏
      description: Cast conversations to large display
      description_zh: 把对话投射到电视/大屏
      device_groups:
        - id: voice_assistant
          type: single
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher
        - id: edge_device
          name: Edge Computing Device
          type: single
          options:
            - device_ref: recomputer_r1000
          default: recomputer_r1000
      architecture_image: intro/gallery/architecture.svg
      # 投屏功能的部署步骤
      devices:
        - id: display_watcher
          name: Flash Watcher Firmware
          name_zh: 烧录 Watcher 固件
          type: esp32_usb
          required: true
          config_file: devices/display_watcher.yaml
          section:
            title: "Step 1: Flash Watcher Firmware"
            title_zh: "第一步：烧录 Watcher 固件"
            description_file: deploy/sections/display_watcher.md
        - id: display_service
          name: Deploy Display Service
          name_zh: 部署投屏服务
          type: docker_deploy
          required: true
          section:
            title: "Step 2: Deploy Display Service"
            title_zh: "第二步：部署投屏服务"
          targets:
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/display_local.yaml
              section:
                description_file: deploy/sections/display_local.md
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/recomputer.yaml
              section:
                description_file: deploy/sections/display_remote.md

# ========== 部署配置（设备已移至 preset.devices） ==========
deployment:
  selection_mode: sequential
  devices: []
  order: []
```

---

## 最佳实践

### 1. 合理设计 Preset

- **按规模分**：入门版、标准版、企业版
- **按场景分**：家用、商用、工业
- **按功能分**：基础功能、增强功能（如示例 2）
- **每个 preset 独立**：不同 preset 可以有完全不同的部署步骤

### 2. preset.devices 设计原则

```yaml
# ✅ 推荐：每个 preset 定义完整的 devices 列表
presets:
  - id: cloud
    devices:
      - id: step1
      - id: step2
      - id: step3_cloud  # 云方案特有步骤
  - id: edge
    devices:
      - id: step1
      - id: step2
      - id: step3_edge   # 边缘方案特有步骤
      - id: step4_edge   # 边缘方案额外步骤

# ❌ 避免：不要使用 show_when 条件（已废弃）
deployment:
  devices:
    - id: step1
      show_when:
        preset: cloud    # 已废弃，请使用 preset.devices
```

### 3. 设备目录复用

- 同类设备不同型号使用不同 key（如 `gateway_us915`、`gateway_eu868`）
- 通用属性放在设备定义中，特定描述放在 device_group 的 label

### 4. 文件组织

```
solutions/your_solution/
├── solution.yaml
├── intro/
│   ├── description.md        # 通用介绍
│   └── gallery/
│       ├── cover.png         # 封面图
│       ├── starter_arch.png  # 入门版架构图
│       ├── standard_arch.png # 标准版架构图
│       └── enterprise_arch.png
├── deploy/
│   ├── guide.md              # 通用部署指南
│   └── sections/
│       ├── step1.md          # 通用步骤
│       ├── step1_zh.md
│       ├── step1_troubleshoot.md
│       ├── starter_tips.md   # preset 专属内容
│       └── enterprise_tips.md
└── devices/
    ├── app_local.yaml
    └── app_remote.yaml
```

### 5. 国际化规范

- 所有面向用户的字段都应提供 `_zh` 版本
- 文件名使用 `filename.md` / `filename_zh.md` 格式
- YAML 字段使用 `field` / `field_zh` 格式

### 6. 测试清单

- [ ] 每个 preset 都有 `devices` 列表
- [ ] 每个 preset 的 devices 列表顺序正确
- [ ] `deployment.devices` 和 `deployment.order` 为空数组
- [ ] 设备组的 default 值存在于 options 中
- [ ] 所有引用的文件路径都存在
- [ ] 中英文版本内容完整
- [ ] device_ref 指向存在的 device_catalog 条目

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目总体开发指南
- [文案编写规范](../.claude/skills/solution-copywriting/SKILL.md) - Markdown 内容编写规范
