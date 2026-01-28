# SenseCraft Solution 配置指南

本文档详细说明如何配置 IoT 解决方案，包括目录结构、YAML 配置字段、以及 Preset（预设套餐）模式的使用。

---

## 目录

1. [目录结构](#目录结构)
2. [solution.yaml 配置详解](#solutionyaml-配置详解)
   - [基础信息](#基础信息)
   - [介绍页配置 (intro)](#介绍页配置-intro)
   - [设备目录 (device_catalog)](#设备目录-device_catalog)
   - [预设套餐 (presets)](#预设套餐-presets)
   - [设备组 (device_groups)](#设备组-device_groups)
   - [Preset 部署设备 (preset.devices)](#preset-部署设备-presetdevices)
   - [部署配置 (deployment)](#部署配置-deployment)
3. [设备配置文件](#设备配置文件)
4. [完整示例](#完整示例)
5. [最佳实践](#最佳实践)

---

## 目录结构

```
solutions/
└── your_solution_id/
    ├── solution.yaml           # 主配置文件（必须）
    │
    ├── intro/                   # 介绍页内容
    │   ├── description.md       # 英文详细介绍
    │   ├── description_zh.md    # 中文详细介绍
    │   ├── gallery/             # 图片资源
    │   │   ├── cover.png        # 封面图（显示在方案卡片）
    │   │   ├── architecture.png # 系统架构图
    │   │   ├── demo.png         # 效果演示图
    │   │   └── device.png       # 设备图片
    │   └── partners/            # 合作伙伴 Logo（可选）
    │       └── partner1.png
    │
    ├── deploy/                  # 部署页内容
    │   ├── guide.md             # 部署指南总览（英文）
    │   ├── guide_zh.md          # 部署指南总览（中文）
    │   ├── success.md           # 部署成功提示（英文）
    │   ├── success_zh.md        # 部署成功提示（中文）
    │   └── sections/            # 各步骤详细说明
    │       ├── step1.md                 # 步骤1说明（英文）
    │       ├── step1_zh.md              # 步骤1说明（中文）
    │       ├── step1_troubleshoot.md    # 步骤1故障排除（可选）
    │       └── ...
    │
    └── devices/                 # 设备部署配置
        ├── device1.yaml         # Docker 部署配置
        ├── device2.yaml         # ESP32 烧录配置
        └── ...
```

### 各目录用途说明

| 目录/文件 | 用途 | 必须 |
|-----------|------|------|
| `solution.yaml` | 方案主配置文件，定义所有元数据 | 是 |
| `intro/description.md` | 介绍页详细描述，支持 Markdown | 是 |
| `intro/gallery/` | 存放方案相关图片（封面、架构图、设备图等） | 是 |
| `intro/partners/` | 合作伙伴 Logo 图片 | 否 |
| `deploy/guide.md` | 部署页顶部的总体说明 | 是 |
| `deploy/sections/` | 各部署步骤的详细 Markdown 说明 | 是 |
| `deploy/success.md` | 部署完成后的成功提示 | 否 |
| `devices/` | 设备部署配置文件（Docker、ESP32 等） | 视情况 |

---

## solution.yaml 配置详解

### 基础信息

```yaml
version: "1.0"                              # 配置版本
id: smart_warehouse                         # 唯一标识符（英文小写+下划线，用于 URL）
name: Smart Warehouse Management            # 英文名称
name_zh: 智慧仓管方案                         # 中文名称
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `version` | string | 是 | 配置版本，当前为 "1.0" |
| `id` | string | 是 | 唯一标识符，用于 URL 路由，只能包含小写字母、数字、下划线 |
| `name` | string | 是 | 英文名称，显示在页面标题 |
| `name_zh` | string | 是 | 中文名称 |

---

### 介绍页配置 (intro)

介绍页展示方案的概述、设备、套餐选择等信息。

```yaml
intro:
  # ===== 基本信息 =====
  summary: One-line description of the solution
  summary_zh: 一句话描述方案

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md

  cover_image: intro/gallery/cover.png

  # ===== 图库 =====
  gallery:
    - type: image
      src: intro/gallery/demo.png
      caption: Demo screenshot
      caption_zh: 演示截图

  # ===== 分类和标签 =====
  category: voice_ai
  tags:
    - iot
    - voice
    - watcher

  # ===== 设备目录 =====
  device_catalog:
    # ... 详见下一节

  # ===== 预设套餐 =====
  presets:
    # ... 详见预设套餐章节

  # ===== 统计信息 =====
  stats:
    difficulty: beginner
    estimated_time: 30min
    deployed_count: 0
    likes_count: 0

  # ===== 外部链接 =====
  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

  # ===== 合作伙伴 =====
  partners:
    # ... 详见合作伙伴章节
```

#### intro 基本字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `summary` | string | 是 | 英文摘要，显示在方案卡片和标题下方 |
| `summary_zh` | string | 是 | 中文摘要 |
| `description_file` | string | 是 | 英文详细介绍 Markdown 文件路径 |
| `description_file_zh` | string | 是 | 中文详细介绍 Markdown 文件路径 |
| `cover_image` | string | 是 | 封面图片路径，显示在方案卡片 |
| `category` | string | 是 | 分类：`voice_ai`, `sensing`, `automation`, `smart_building` 等 |
| `tags` | list | 否 | 标签列表，用于筛选和搜索 |

#### gallery（图库）

```yaml
gallery:
  - type: image                          # 类型：image | video
    src: intro/gallery/demo.png          # 文件路径
    caption: Demo screenshot             # 英文说明
    caption_zh: 演示截图                  # 中文说明
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 媒体类型：`image` 或 `video` |
| `src` | string | 是 | 文件路径（相对于 solution 目录） |
| `caption` | string | 否 | 英文说明文字 |
| `caption_zh` | string | 否 | 中文说明文字 |

#### stats（统计信息）

```yaml
stats:
  difficulty: beginner           # 难度级别
  estimated_time: 30min          # 预计部署时间
  deployed_count: 0              # 已部署次数（自动统计）
  likes_count: 0                 # 点赞数（自动统计）
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `difficulty` | string | 难度：`beginner`（入门）、`intermediate`（中级）、`advanced`（高级） |
| `estimated_time` | string | 预计时间，如 `30min`、`1h`、`2h` |
| `deployed_count` | number | 部署次数（系统自动更新） |
| `likes_count` | number | 点赞数（系统自动更新） |

#### links（外部链接）

```yaml
links:
  wiki: https://wiki.seeedstudio.com/...     # Wiki 文档链接
  github: https://github.com/...              # GitHub 仓库链接
```

#### partners（合作伙伴）

定义可提供现场部署服务的合作伙伴。

```yaml
partners:
  - name: Seeed Technology                  # 英文名称
    name_zh: 深圳矽递科技                    # 中文名称
    logo: intro/partners/seeed.png          # Logo 图片路径
    website: https://www.seeedstudio.com    # 官网链接
    regions:                                 # 服务地区（中文）
      - 广东省
      - 全国远程
    regions_en:                              # 服务地区（英文）
      - Guangdong
      - Remote (China)
    contact: solutions@seeed.cc             # 联系方式
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 合作伙伴英文名称 |
| `name_zh` | string | 是 | 合作伙伴中文名称 |
| `logo` | string | 否 | Logo 图片路径 |
| `website` | string | 否 | 官网链接 |
| `regions` | list | 是 | 服务地区列表（中文） |
| `regions_en` | list | 否 | 服务地区列表（英文） |
| `contact` | string | 是 | 联系邮箱或电话 |

---

### 设备目录 (device_catalog)

定义方案中涉及的所有硬件设备。这是一个**字典结构**，key 为设备引用 ID，在 `device_groups` 中通过 `device_ref` 引用。

```yaml
intro:
  device_catalog:
    # key 是设备引用 ID，用于 device_groups 中的 device_ref
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: intro/gallery/watcher.png
      product_url: https://www.seeedstudio.com/sensecap-watcher
      wiki_url: https://wiki.seeedstudio.com/watcher/
      description: AI-powered wearable voice assistant (ESP32-S3)
      description_zh: AI 驱动的可穿戴语音助手（ESP32-S3）
      category: voice_assistant

    recomputer_r1100:
      name: reComputer R1100
      name_zh: reComputer R1100
      image: intro/gallery/r1100.png
      product_url: https://www.seeedstudio.com/recomputer-r1100
      description: Edge gateway for warehouse system
      description_zh: 边缘网关，运行仓管系统

    # 同类设备的不同版本（如不同频段）
    gateway_us915:
      name: SenseCAP M2 Gateway (US915)
      name_zh: SenseCAP M2 网关 (US915)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...-US915
      description: LoRaWAN gateway for Americas
      description_zh: 美洲地区 LoRaWAN 网关

    gateway_eu868:
      name: SenseCAP M2 Gateway (EU868)
      name_zh: SenseCAP M2 网关 (EU868)
      image: intro/gallery/gateway.png
      product_url: https://www.seeedstudio.com/...-EU868
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 设备英文名称 |
| `name_zh` | string | 否 | 设备中文名称 |
| `image` | string | 否 | 设备图片路径 |
| `product_url` | string | 否 | 产品购买链接 |
| `wiki_url` | string | 否 | Wiki 文档链接 |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `category` | string | 否 | 设备类别 |

---

### 预设套餐 (presets)

**核心功能**：定义不同规模/场景的部署方案，用户可以选择不同套餐。

每个 preset 包含：
- **基本信息**：名称、描述、角标
- **device_groups**：该套餐需要的设备选择（显示在介绍页）
- **devices**：该套餐的完整部署步骤（显示在部署页）
- **section**：该套餐的部署指南说明
- **links**：该套餐专属的链接

```yaml
intro:
  presets:
    - id: sensecraft_cloud                    # 套餐唯一标识
      name: SenseCraft Cloud                  # 英文名称
      name_zh: SenseCraft 云方案              # 中文名称
      badge: Recommended                      # 角标（显示在套餐卡片）
      badge_zh: 推荐                          # 中文角标
      description: Use SenseCraft cloud       # 英文描述
      description_zh: 使用 SenseCraft 云平台   # 中文描述

      # 设备组（介绍页设备选择）
      device_groups:
        - id: watcher
          name: Voice Assistant
          name_zh: 语音助手
          type: single
          required: true
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher

      # 该套餐的架构图
      architecture_image: intro/gallery/architecture-cloud.png

      # 该套餐专属链接
      links:
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...

      # 该套餐的部署指南
      section:
        title: Cloud Deployment Guide
        title_zh: 云方案部署指南
        description_file: deploy/sections/cloud_guide.md
        description_file_zh: deploy/sections/cloud_guide_zh.md

      # 该套餐的部署步骤（完整列表）
      devices:
        - id: warehouse
          name: Warehouse System
          # ... 完整设备配置
        - id: voice_service
          # ...
```

#### preset 基本字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 套餐唯一标识 |
| `name` | string | 是 | 英文名称 |
| `name_zh` | string | 是 | 中文名称 |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `badge` | string | 否 | 英文角标（如 "Recommended"、"Popular"） |
| `badge_zh` | string | 否 | 中文角标（如 "推荐"、"热门"） |
| `device_groups` | list | 否 | 设备组定义，用于介绍页设备选择 |
| `architecture_image` | string | 否 | 该套餐的架构图路径 |
| `links` | object | 否 | 该套餐专属链接（wiki、github） |
| `section` | object | 否 | 套餐专属的部署指南 |
| `devices` | list | **是** | 该套餐的完整部署步骤列表 |

#### preset.section（套餐部署指南）

```yaml
section:
  title: Cloud Deployment Guide           # 英文标题
  title_zh: 云方案部署指南                  # 中文标题
  description_file: deploy/sections/cloud_guide.md
  description_file_zh: deploy/sections/cloud_guide_zh.md
```

---

### 设备组 (device_groups)

定义用户在介绍页可以选择的设备组合。支持三种类型：

#### 1. single 类型 - 单选

用于同类设备中只能选择一个的情况。

```yaml
device_groups:
  - id: gateway                           # 组 ID
    name: LoRaWAN Gateway                 # 英文名称
    name_zh: LoRaWAN 网关                  # 中文名称
    type: single                          # 单选类型
    required: true                        # 是否必选
    description: Select gateway for your region
    description_zh: 选择您所在地区的网关
    options:                              # 选项列表
      - device_ref: gateway_us915         # 引用 device_catalog 中的 key
        label: Americas (US915)           # 英文选项标签
        label_zh: 美洲 (US915)             # 中文选项标签
      - device_ref: gateway_eu868
        label: Europe (EU868)
        label_zh: 欧洲 (EU868)
    default: gateway_us915                # 默认选中项
```

#### 2. quantity 类型 - 数量选择

用于需要指定数量的设备。

```yaml
  - id: beacons
    name: BLE Beacons
    name_zh: BLE 信标
    type: quantity                        # 数量类型
    required: true
    device_ref: bc01_beacon               # 引用单个设备
    min_count: 3                          # 最小数量
    max_count: 100                        # 最大数量
    default_count: 6                      # 默认数量
    description: "Recommended: 3-5 per zone"
    description_zh: "建议：每个区域 3-5 个"
```

#### 3. multiple 类型 - 多选

用于可以选择多个不同设备的情况。

```yaml
  - id: sensors
    name: Additional Sensors
    name_zh: 附加传感器
    type: multiple                        # 多选类型
    required: false
    min_count: 0
    max_count: 5
    options:
      - device_ref: temp_sensor
        label: Temperature Sensor
        label_zh: 温度传感器
      - device_ref: humidity_sensor
        label: Humidity Sensor
        label_zh: 湿度传感器
    default_selections:                   # 默认选中的项
      - temp_sensor
```

#### device_groups 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 设备组 ID |
| `name` | string | 是 | 英文名称 |
| `name_zh` | string | 否 | 中文名称 |
| `type` | string | 是 | 类型：`single`、`quantity`、`multiple` |
| `required` | boolean | 否 | 是否必选，默认 false |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `options` | list | single/multiple 必填 | 选项列表 |
| `device_ref` | string | quantity 必填 | 引用 device_catalog 中的设备 |
| `default` | string | 否 | 默认选中的 device_ref（single 类型） |
| `default_count` | number | 否 | 默认数量（quantity 类型） |
| `default_selections` | list | 否 | 默认选中列表（multiple 类型） |
| `min_count` | number | 否 | 最小数量 |
| `max_count` | number | 否 | 最大数量 |

---

### Preset 部署设备 (preset.devices)

每个 preset 包含自己独立的 `devices` 列表，定义该套餐的完整部署流程。

#### 设备类型 (type)

| 类型 | 说明 | 用途 |
|------|------|------|
| `manual` | 手动操作步骤 | 需要用户手动完成的配置、安装等 |
| `esp32_usb` | ESP32 固件烧录 | 通过 USB 烧录 ESP32 系列固件 |
| `himax_usb` | Himax 固件烧录 | 通过 USB 烧录 Himax WE2 固件 |
| `docker_deploy` | Docker 部署 | 支持本地/远程 Docker 容器部署 |
| `script` | 脚本执行 | 运行自定义脚本 |
| `preview` | 实时预览 | 显示视频流或实时数据 |

#### 设备基本结构

```yaml
devices:
  - id: unique_step_id                    # 步骤唯一标识
    name: Step Name                       # 英文名称
    name_zh: 步骤名称                      # 中文名称
    type: manual                          # 类型
    required: true                        # 是否必须完成
    config_file: devices/xxx.yaml         # 设备配置文件（部分类型需要）
    section:                              # 步骤说明
      title: Step Title
      title_zh: 步骤标题
      description_file: deploy/sections/step.md
      description_file_zh: deploy/sections/step_zh.md
      troubleshoot_file: deploy/sections/step_troubleshoot.md
      wiring:                             # 接线/配置步骤图示
        image: intro/gallery/wiring.png
        steps:
          - Step 1 instruction
          - Step 2 instruction
        steps_zh:
          - 步骤1说明
          - 步骤2说明
```

#### section 字段详解

`section` 定义步骤的详细说明内容：

```yaml
section:
  title: Deploy Warehouse System          # 英文标题（显示在步骤卡片）
  title_zh: 部署仓库管理系统                # 中文标题
  description_file: deploy/sections/warehouse.md       # 英文说明文件
  description_file_zh: deploy/sections/warehouse_zh.md # 中文说明文件
  troubleshoot_file: deploy/sections/warehouse_troubleshoot.md  # 故障排除（可选）
  wiring:                                 # 接线/配置步骤图示
    image: intro/gallery/diagram.png      # 示意图路径
    steps:                                # 英文步骤列表（显示在图片旁）
      - Connect device via USB-C
      - Select the serial port
      - Click Deploy button
    steps_zh:                             # 中文步骤列表
      - 通过 USB-C 连接设备
      - 选择串口
      - 点击部署按钮
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 否 | 英文标题 |
| `title_zh` | string | 否 | 中文标题 |
| `description_file` | string | 是 | 英文说明 Markdown 文件路径 |
| `description_file_zh` | string | 是 | 中文说明 Markdown 文件路径 |
| `troubleshoot_file` | string | 否 | 故障排除 Markdown 文件路径 |
| `wiring` | object | 否 | 接线/配置步骤图示 |
| `wiring.image` | string | 否 | 示意图路径 |
| `wiring.steps` | list | 否 | 英文步骤列表 |
| `wiring.steps_zh` | list | 否 | 中文步骤列表 |

#### targets（多目标部署）

`docker_deploy` 类型支持多个部署目标（如本地部署、远程部署）：

```yaml
devices:
  - id: warehouse
    name: Warehouse System
    name_zh: 仓库管理系统
    type: docker_deploy
    required: true
    config_file: devices/warehouse_local.yaml    # 默认配置
    section:
      title: Deploy Warehouse System
      title_zh: 部署仓库管理系统
    targets:                                      # 多个部署目标
      local:                                      # 目标 ID
        name: Local Deployment                    # 英文名称
        name_zh: 本机部署                          # 中文名称
        description: Deploy on this computer      # 英文描述
        description_zh: 部署到当前电脑             # 中文描述
        default: true                             # 是否默认选中
        config_file: devices/warehouse_local.yaml # 该目标的配置文件
        section:                                  # 该目标专属的说明
          description_file: deploy/sections/warehouse_local.md
          description_file_zh: deploy/sections/warehouse_local_zh.md
          wiring:
            image: intro/gallery/local-deploy.png
            steps:
              - Ensure Docker is installed and running
              - Click Deploy button to start services
            steps_zh:
              - 确保 Docker 已安装并运行
              - 点击部署按钮启动服务

      remote:                                     # 远程部署目标
        name: Remote Deployment
        name_zh: 远程部署
        description: Deploy to a remote device via SSH
        description_zh: 通过 SSH 部署到远程设备
        config_file: devices/warehouse_remote.yaml
        section:
          description_file: deploy/sections/warehouse_remote.md
          description_file_zh: deploy/sections/warehouse_remote_zh.md
          wiring:
            image: intro/gallery/remote-deploy.png
            steps:
              - Connect target device to network
              - Enter IP address and SSH credentials
              - Click Deploy to install on remote device
            steps_zh:
              - 将目标设备连接到网络
              - 输入 IP 地址和 SSH 凭据
              - 点击部署安装到远程设备
```

#### targets 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 英文名称 |
| `name_zh` | string | 是 | 中文名称 |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `default` | boolean | 否 | 是否默认选中（只能有一个为 true） |
| `config_file` | string | 是 | 该目标的设备配置文件路径 |
| `section` | object | 否 | 该目标专属的说明内容 |

---

### 部署配置 (deployment)

部署设备定义在各 `preset.devices` 中，`deployment` 节点仅保留全局配置。

```yaml
deployment:
  # 部署指南（显示在部署页顶部）
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md

  # 部署模式
  selection_mode: sequential              # sequential | single_choice

  # 部署后操作
  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps:
      - title: Access Web Interface
        title_zh: 访问 Web 界面
        action: open_url
        url: "http://localhost:2125"
      - title: View Wiki Documentation
        title_zh: 查看 Wiki 文档
        action: open_url
        url: "https://wiki.seeedstudio.com/..."
```

#### deployment 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `guide_file` | string | 否 | 英文部署指南文件路径 |
| `guide_file_zh` | string | 否 | 中文部署指南文件路径 |
| `selection_mode` | string | 否 | 部署模式：`sequential`（按顺序）、`single_choice`（单选） |
| `post_deployment` | object | 否 | 部署完成后的操作 |

#### post_deployment 字段说明

```yaml
post_deployment:
  success_message_file: deploy/success.md      # 成功提示文件（英文）
  success_message_file_zh: deploy/success_zh.md # 成功提示文件（中文）
  next_steps:                                   # 后续操作按钮
    - title: Access Dashboard                   # 英文按钮文字
      title_zh: 访问仪表板                       # 中文按钮文字
      action: open_url                          # 动作类型：open_url
      url: "http://localhost:5173"              # 要打开的 URL
```

---

## 设备配置文件

设备配置文件放在 `devices/` 目录下，定义具体的部署参数。

### Docker 本地部署配置

```yaml
# devices/warehouse_local.yaml
version: "1.0"
id: warehouse_local
name: Warehouse System (Local)
name_zh: 仓库管理系统（本机）
type: docker_local

detection:
  method: local
  requirements:
    - docker_installed
    - docker_running

docker:
  image: seeedcloud/warehouse-system
  container_name: warehouse-system
  ports:
    - "2125:2125"
  volumes:
    - ./db:/app/db/
    - ./config:/app/config
  environment:
    - NODE_ENV=production
  restart: unless-stopped

  services:
    - name: warehouse-system
      port: 2125
      health_check_endpoint: /api/health
      required: true

  images:
    - name: seeedcloud/warehouse-system
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
  url: "http://localhost:2125"
  credentials:
    username: admin
    password: admin123
```

### Docker 远程部署配置

```yaml
# devices/warehouse_remote.yaml
version: "1.0"
id: warehouse_remote
name: Warehouse System (Remote)
name_zh: 仓库管理系统（远程）
type: docker_ssh

detection:
  method: ssh
  requirements:
    - ssh_reachable
    - docker_installed
    - docker_running

ssh:
  port: 22
  username: root                         # 默认用户名

user_inputs:
  - id: ssh_host
    name: SSH Host
    name_zh: SSH 主机地址
    type: text
    required: true
    placeholder: "192.168.1.100"

  - id: ssh_password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    required: true

docker:
  image: seeedcloud/warehouse-system
  container_name: warehouse-system
  ports:
    - "2125:2125"
  restart: unless-stopped
```

### ESP32 固件烧录配置

```yaml
# devices/watcher_esp32.yaml
version: "1.0"
id: watcher_esp32
name: Watcher ESP32 Firmware
name_zh: Watcher ESP32 固件
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"
  fallback_ports:
    - "/dev/tty.wchusbserial*"
    - "/dev/cu.wchusbserial*"
    - "/dev/ttyUSB*"
    - "COM*"

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

### 脚本执行配置

```yaml
# devices/mcp_bridge.yaml
version: "1.0"
id: mcp_bridge
name: MCP Bridge Service
name_zh: MCP 桥接服务
type: script

user_inputs:
  - id: mcp_endpoint
    name: MCP Endpoint
    name_zh: MCP 端点
    type: text
    required: true
    placeholder: "wss://xxx.sensecraft.cc/mcp"

  - id: api_key
    name: API Key
    name_zh: API 密钥
    type: text
    required: true

script:
  command: "./start_bridge.sh"
  args:
    - "--endpoint={{mcp_endpoint}}"
    - "--api-key={{api_key}}"
  working_dir: scripts/
  background: true
```

---

## 完整示例

### 示例：智慧仓管方案（多 Preset）

```yaml
version: "1.0"
id: smart_warehouse
name: Smart Warehouse Management
name_zh: 智慧仓管方案

intro:
  summary: Voice-controlled warehouse operations
  summary_zh: 语音操控仓库管理

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md
  cover_image: intro/gallery/cover.png

  gallery:
    - type: image
      src: intro/gallery/architecture.png
      caption: System architecture
      caption_zh: 系统架构图

  category: voice_ai
  tags: [mcp, voice, watcher, warehouse]

  # ===== 设备目录 =====
  device_catalog:
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: intro/gallery/watcher.png
      product_url: https://www.seeedstudio.com/sensecap-watcher
      description: AI-powered voice assistant (ESP32-S3)
      description_zh: AI 语音助手（ESP32-S3）

    recomputer_r1100:
      name: reComputer R1100
      name_zh: reComputer R1100
      image: intro/gallery/r1100.png
      product_url: https://www.seeedstudio.com/recomputer-r1100

  # ===== 预设套餐 =====
  presets:
    # ----- 云方案 -----
    - id: sensecraft_cloud
      name: SenseCraft Cloud
      name_zh: SenseCraft 云方案
      badge: Recommended
      badge_zh: 推荐
      description: Use SenseCraft cloud for device management
      description_zh: 使用 SenseCraft 云平台进行设备管理
      device_groups:
        - id: watcher
          name: Voice Assistant
          name_zh: 语音助手
          type: single
          required: true
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher
      architecture_image: intro/gallery/architecture-cloud.png
      links:
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...
      section:
        title: Cloud Deployment Guide
        title_zh: 云方案部署指南
        description_file: deploy/sections/cloud_guide.md
        description_file_zh: deploy/sections/cloud_guide_zh.md
      devices:
        - id: warehouse
          name: Warehouse System
          name_zh: 仓库管理系统
          type: docker_deploy
          required: true
          config_file: devices/warehouse_local.yaml
          section:
            title: Deploy Warehouse System
            title_zh: 部署仓库管理系统
          targets:
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/warehouse_local.yaml
              section:
                description_file: deploy/sections/warehouse_local.md
                description_file_zh: deploy/sections/warehouse_local_zh.md
                wiring:
                  image: intro/gallery/local.png
                  steps:
                    - Ensure Docker is installed
                    - Click Deploy button
                  steps_zh:
                    - 确保 Docker 已安装
                    - 点击部署按钮
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/warehouse_remote.yaml
              section:
                description_file: deploy/sections/warehouse_remote.md
                description_file_zh: deploy/sections/warehouse_remote_zh.md
        - id: sensecraft
          name: SenseCraft Platform
          name_zh: SenseCraft 平台配置
          type: manual
          required: true
          section:
            title: Configure SenseCraft
            title_zh: 配置 SenseCraft
            description_file: deploy/sections/sensecraft.md
            description_file_zh: deploy/sections/sensecraft_zh.md
            wiring:
              image: intro/gallery/sensecraft.png
              steps:
                - Power on the Watcher
                - Connect to WiFi via QR code
                - Login to SenseCraft platform
              steps_zh:
                - 开启 Watcher 电源
                - 扫码连接 WiFi
                - 登录 SenseCraft 平台

    # ----- 私有云方案 -----
    - id: private_cloud
      name: Private Cloud
      name_zh: 私有云方案
      description: Self-hosted deployment
      description_zh: 自托管部署
      # ... 设备组和部署步骤配置

  stats:
    difficulty: beginner
    estimated_time: 30min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

  partners:
    - name: Seeed Technology
      name_zh: 深圳矽递科技
      logo: intro/partners/seeed.png
      website: https://www.seeedstudio.com
      regions:
        - 广东省
      regions_en:
        - Guangdong
      contact: solutions@seeed.cc

deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  selection_mode: sequential

  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps:
      - title: Access Web Interface
        title_zh: 访问 Web 界面
        action: open_url
        url: "http://localhost:2125"
```

---

## 最佳实践

### 1. 目录组织

```
solutions/your_solution/
├── solution.yaml
├── intro/
│   ├── description.md
│   ├── description_zh.md
│   └── gallery/
│       ├── cover.png              # 封面图（必须）
│       ├── architecture-cloud.png # 云方案架构图
│       ├── architecture-edge.png  # 边缘方案架构图
│       └── devices/               # 设备图片（可选子目录）
├── deploy/
│   ├── guide.md
│   ├── guide_zh.md
│   ├── success.md
│   ├── success_zh.md
│   └── sections/
│       ├── cloud_guide.md         # 云方案指南
│       ├── cloud_guide_zh.md
│       ├── warehouse_local.md     # 本地部署说明
│       ├── warehouse_local_zh.md
│       └── ...
└── devices/
    ├── warehouse_local.yaml
    ├── warehouse_remote.yaml
    └── ...
```

### 2. Preset 设计原则

- **按规模分**：入门版、标准版、企业版
- **按场景分**：云方案、私有云、边缘计算
- **每个 preset 独立**：不同 preset 可以有完全不同的部署步骤
- **不使用 show_when**：已废弃，直接在 preset.devices 中定义

### 3. 国际化规范

- 所有面向用户的字段都应提供 `_zh` 版本
- 文件名使用 `filename.md` / `filename_zh.md` 格式
- YAML 字段使用 `field` / `field_zh` 格式

### 4. 测试清单

- [ ] 每个 preset 都有 `devices` 列表
- [ ] 每个 preset 的 devices 顺序正确
- [ ] 所有 `device_ref` 指向存在的 `device_catalog` 条目
- [ ] 所有引用的文件路径都存在
- [ ] 中英文版本内容完整
- [ ] `targets` 中只有一个 `default: true`

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目总体开发指南
- [文案编写规范](../.claude/skills/solution-copywriting/SKILL.md) - Markdown 内容编写规范
