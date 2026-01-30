# SenseCraft Solution 配置指南

本文档详细说明如何配置 IoT 解决方案，包括目录结构、YAML 配置字段、以及 Markdown 部署指南格式。

---

## 目录

1. [目录结构](#目录结构)
2. [solution.yaml 配置详解](#solutionyaml-配置详解)
   - [基础信息](#基础信息)
   - [介绍页配置 (intro)](#介绍页配置-intro)
   - [预设套餐 (presets)](#预设套餐-presets)
   - [部署配置 (deployment)](#部署配置-deployment)
3. [guide.md 部署指南格式](#guidemd-部署指南格式)
   - [Preset 定义](#preset-定义)
   - [Step 定义](#step-定义)
   - [Target 定义](#target-定义)
   - [完整示例](#guidemd-完整示例)
4. [设备配置文件](#设备配置文件)
5. [完整示例](#完整示例)
6. [最佳实践](#最佳实践)

---

## 目录结构

```
solutions/
└── your_solution_id/
    ├── solution.yaml           # 主配置文件（必须）
    ├── description.md          # 英文详细介绍（必须）
    ├── description_zh.md       # 中文详细介绍（必须）
    ├── guide.md                # 英文部署指南（必须）
    ├── guide_zh.md             # 中文部署指南（必须）
    │
    ├── gallery/                # 图片资源
    │   ├── cover.png           # 封面图（显示在方案卡片）
    │   ├── architecture.png    # 系统架构图
    │   ├── demo.png            # 效果演示图
    │   └── device.png          # 设备图片
    │
    └── devices/                # 设备部署配置
        ├── device1.yaml        # Docker 部署配置
        ├── device2.yaml        # ESP32 烧录配置
        └── ...
```

### 各文件用途说明

| 文件/目录 | 用途 | 必须 |
|-----------|------|------|
| `solution.yaml` | 方案主配置文件，定义元数据和预设套餐 | 是 |
| `description.md` | 介绍页详细描述（英文），支持 Markdown | 是 |
| `description_zh.md` | 介绍页详细描述（中文） | 是 |
| `guide.md` | 部署指南（英文），包含步骤定义和说明 | 是 |
| `guide_zh.md` | 部署指南（中文） | 是 |
| `gallery/` | 存放方案相关图片（封面、架构图、设备图等） | 是 |
| `devices/` | 设备部署配置文件（Docker、ESP32 等） | 视情况 |

> **注意**：所有 Markdown 文件直接放在方案根目录，不再使用 `intro/` 和 `deploy/` 子目录。

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

  # 直接在根目录的文件路径
  description_file: description.md
  description_file_zh: description_zh.md

  cover_image: gallery/cover.png

  # ===== 图库 =====
  gallery:
    - type: image
      src: gallery/demo.png
      caption: Demo screenshot
      caption_zh: 演示截图

  # ===== 分类和标签 =====
  category: voice_ai
  tags:
    - iot
    - voice
    - watcher

  # ===== 预设套餐 =====
  presets:
    # ... 详见预设套餐章节

  # ===== 统计信息 =====
  stats:
    difficulty: beginner
    estimated_time: 30min

  # ===== 外部链接 =====
  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

  # ===== 合作伙伴（可选）=====
  partners:
    # ... 详见合作伙伴章节
```

#### intro 基本字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `summary` | string | 是 | 英文摘要，显示在方案卡片和标题下方 |
| `summary_zh` | string | 是 | 中文摘要 |
| `description_file` | string | 是 | 英文详细介绍 Markdown 文件路径（相对于方案目录） |
| `description_file_zh` | string | 是 | 中文详细介绍 Markdown 文件路径 |
| `cover_image` | string | 是 | 封面图片路径，显示在方案卡片 |
| `category` | string | 是 | 分类：`voice_ai`, `sensing`, `automation`, `smart_building` 等 |
| `tags` | list | 否 | 标签列表，用于筛选和搜索 |

#### gallery（图库）

```yaml
gallery:
  - type: image                          # 类型：image | video
    src: gallery/demo.png                # 文件路径（相对于方案目录）
    caption: Demo screenshot             # 英文说明
    caption_zh: 演示截图                  # 中文说明
```

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
    logo: gallery/partners/seeed.png        # Logo 图片路径
    website: https://www.seeedstudio.com    # 官网链接
    regions:                                 # 服务地区（中文）
      - 广东省
      - 全国远程
    regions_en:                              # 服务地区（英文）
      - Guangdong
      - Remote (China)
    contact: solutions@seeed.cc             # 联系方式
```

---

### 预设套餐 (presets)

**核心功能**：定义不同规模/场景的部署方案，用户可以选择不同套餐。

**重要变化**：预设的具体部署步骤现在定义在 `guide.md` 文件中，而不是在 YAML 里。

```yaml
intro:
  presets:
    - id: sensecraft_cloud                    # 套餐唯一标识（对应 guide.md 中的 {#sensecraft_cloud}）
      name: SenseCraft Cloud                  # 英文名称
      name_zh: 云方案                          # 中文名称
      badge: Recommended                      # 角标（显示在套餐卡片）
      badge_zh: 推荐                          # 中文角标
      description: Use SenseCraft cloud       # 英文描述
      description_zh: 使用 SenseCraft 云平台   # 中文描述

    - id: private_cloud
      name: Private Cloud
      name_zh: 私有云方案
      description: Self-hosted deployment
      description_zh: 自托管部署

    - id: edge_computing
      name: Edge Computing
      name_zh: 边缘计算方案
      description: Pure LAN deployment
      description_zh: 纯局域网部署
```

#### preset 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 套餐唯一标识，必须与 guide.md 中的 `{#id}` 对应 |
| `name` | string | 是 | 英文名称 |
| `name_zh` | string | 是 | 中文名称 |
| `description` | string | 否 | 英文描述 |
| `description_zh` | string | 否 | 中文描述 |
| `badge` | string | 否 | 英文角标（如 "Recommended"、"Popular"） |
| `badge_zh` | string | 否 | 中文角标（如 "推荐"、"热门"） |

---

### 部署配置 (deployment)

```yaml
deployment:
  # 部署指南文件（直接在根目录）
  guide_file: guide.md
  guide_file_zh: guide_zh.md

  # 部署模式
  selection_mode: sequential              # sequential | single_choice
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `guide_file` | string | 是 | 英文部署指南文件路径 |
| `guide_file_zh` | string | 是 | 中文部署指南文件路径 |
| `selection_mode` | string | 否 | 部署模式：`sequential`（按顺序）、`single_choice`（单选） |

---

## guide.md 部署指南格式

部署指南使用特殊的 Markdown 语法定义预设、步骤和部署目标。系统会解析这些特殊标记来构建部署流程。

### Preset 定义

使用 H2 标题定义预设套餐：

```markdown
## Preset: 套餐名称 {#preset_id}
```

- `Preset:` 前缀标识这是一个套餐定义
- `{#preset_id}` 必须与 solution.yaml 中的 preset id 对应
- 紧随其后的内容是该套餐的介绍文字

**示例**：

```markdown
## Preset: SenseCraft Cloud {#sensecraft_cloud}

使用 SenseCraft 云服务，快速部署、低成本起步。

## Preset: Private Cloud {#private_cloud}

自托管部署，数据隐私要求高的场景。
```

### Step 定义

使用 H2 标题定义部署步骤：

```markdown
## Step N: 步骤名称 {#step_id type=xxx required=xxx config=xxx}
```

**属性说明**：

| 属性 | 必填 | 说明 |
|------|------|------|
| `#step_id` | 是 | 步骤唯一标识 |
| `type` | 是 | 部署类型（见下表） |
| `required` | 否 | 是否必须完成，默认 `true` |
| `config` | 视情况 | 设备配置文件路径 |

**部署类型 (type)**：

| 类型 | 说明 | 是否需要 config |
|------|------|----------------|
| `manual` | 手动操作步骤 | 否 |
| `esp32_usb` | ESP32 固件烧录 | 是 |
| `himax_usb` | Himax WE2 固件烧录 | 是 |
| `docker_deploy` | Docker 部署（支持本地/远程） | 是 |
| `docker_local` | Docker 本地部署 | 是 |
| `docker_remote` | Docker 远程部署 | 是 |
| `recamera_cpp` | reCamera C++ 部署 | 是 |
| `recamera_nodered` | reCamera Node-RED 部署 | 是 |
| `script` | 脚本执行 | 是 |
| `preview` | 实时预览 | 是 |

**示例**：

```markdown
## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse.yaml}

### 说明内容

这里是步骤的详细说明，支持标准 Markdown 格式。

### Troubleshooting

| 问题 | 解决方案 |
|------|----------|
| Docker 未安装 | 安装 Docker Desktop |
```

### Target 定义

在 `docker_deploy` 类型的步骤下，使用 H3 标题定义多个部署目标：

```markdown
### Target: 目标名称 {#target_id config=xxx default=true}
```

**属性说明**：

| 属性 | 必填 | 说明 |
|------|------|------|
| `#target_id` | 是 | 目标唯一标识 |
| `config` | 是 | 该目标的设备配置文件路径 |
| `default` | 否 | 是否默认选中（只能有一个为 true） |

**示例**：

```markdown
## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse.yaml}

### Target: Local Deployment {#warehouse_local config=devices/warehouse_local.yaml}

在本机部署仓库管理系统。

**前提条件**：
- Docker Desktop 已安装并运行
- 端口 2125 可用

### Target: Remote Deployment {#warehouse_remote config=devices/warehouse_remote.yaml default=true}

部署到远程设备（reComputer R1100）。

**操作步骤**：
1. 连接目标设备到网络
2. 输入 IP 地址和 SSH 凭据
3. 点击部署安装到远程设备
```

### guide.md 完整示例

```markdown
## Preset: SenseCraft Cloud {#sensecraft_cloud}

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse.yaml}

### Target: Local Deployment {#warehouse_local config=devices/warehouse_local.yaml}

![架构图](gallery/architecture.png)

1. 确保 Docker 已安装并运行
2. 点击部署按钮启动服务

### Target: Remote Deployment (R1100) {#warehouse_remote config=devices/warehouse_remote.yaml default=true}

![架构图](gallery/architecture.png)

1. 连接目标设备到网络
2. 输入 IP 地址和 SSH 凭据
3. 点击部署安装到远程设备

---

## Step 2: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi.yaml}

### Target: Local Deployment {#voice_local config=devices/xiaozhi_local.yaml}

### Target: Remote Deployment {#voice_remote config=devices/xiaozhi_remote.yaml default=true}

---

## Step 3: SenseCraft Platform {#sensecraft type=manual required=true}

### 操作步骤

![接线图](gallery/wiring.png)

1. 开启 SenseCAP Watcher 电源
2. 扫码连接 WiFi
3. 登录 SenseCraft 平台绑定设备
4. 从 Watcher Agent 设置中获取 MCP Endpoint

---

## Step 4: MCP Bridge Service {#mcp_bridge type=script required=true config=devices/mcp_bridge.yaml}

### 操作步骤

1. 从 SenseCraft 平台获取 MCP endpoint
2. 在仓管系统中创建 API key
3. 配置并启动 MCP 桥接服务

---

## Step 5: Demo & Testing {#demo type=manual required=false}

### 测试方法

1. 对 Watcher 说话查询库存
2. 尝试入库、出库命令
3. 在仓管系统 Web 界面查看结果

---

## Preset: Private Cloud {#private_cloud}

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse.yaml}

（与云方案共享相同步骤定义）

### Target: Local Deployment {#warehouse_local config=devices/warehouse_local.yaml}

### Target: Remote Deployment {#warehouse_remote config=devices/warehouse_remote.yaml default=true}

---

## Step 2: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi.yaml}

### Target: Local Deployment {#voice_local config=devices/xiaozhi_local.yaml}

### Target: Remote Deployment {#voice_remote config=devices/xiaozhi_remote.yaml default=true}

---

## Step 3: Xiaozhi Control Panel {#xiaozhi_console type=manual required=true}

### 操作步骤

1. 访问控制面板 http://server-ip:8002
2. 注册管理员账号（首个用户为管理员）
3. 在模型配置中设置 LLM/TTS API 密钥
4. 从参数页面复制 MCP Endpoint 地址

---

# Deployment Complete

恭喜！您的智慧仓管系统已部署完成。

## 后续步骤

- [访问仓管系统](http://localhost:2125)
- [查看 Wiki 文档](https://wiki.seeedstudio.com/...)
```

### 格式说明

1. **Preset 块**：从 `## Preset:` 开始，到下一个 `## Preset:` 或文件结尾
2. **Step 块**：从 `## Step N:` 开始，到下一个 `## Step` 或 `## Preset:` 或分隔线 `---`
3. **Target 块**：从 `### Target:` 开始，到下一个 `### Target:` 或步骤结束
4. **通用内容**：`# Deployment Complete` 标记部署完成后的内容

### 图片引用

```markdown
![说明文字](gallery/image.png)
```

图片路径相对于方案目录。

### Markdown 内容规范

- 步骤说明使用有序列表 `1. 2. 3.`
- 故障排除使用表格格式
- 分隔线 `---` 用于分隔步骤

### 步骤内容结构

每个步骤（Step）或目标（Target）内部可以使用 H3/H4 小标题来组织内容。系统会识别特定的小标题并进行特殊处理。

#### 系统识别的特殊小标题

| 小标题 | 中文版 | 处理方式 |
|--------|--------|----------|
| `### Troubleshooting` | `### 故障排除` | **单独提取**，显示在部署按钮下方 |

#### 推荐使用的普通小标题

以下小标题不会被特殊处理，按顺序显示在步骤描述区域内：

| 小标题 | 中文版 | 用途 |
|--------|--------|------|
| `### Prerequisites` | `### 前提条件` | 部署前需要准备的环境 |
| `### Steps` | `### 操作步骤` | 手动操作指引 |
| `### After Deployment` | `### 部署完成后` | 部署成功后的验证/配置步骤 |
| `### Notes` | `### 注意事项` | 重要提醒 |
| `### Wiring` | `### 接线` | 硬件接线说明（会提取图片和步骤列表） |

#### 步骤内容完整示例

```markdown
## Step 1: Deploy Backend {#backend type=docker_deploy required=true config=devices/backend.yaml}

### Target: Local Deployment {#backend_local config=devices/backend_local.yaml default=true}

## 本机部署

将后端服务部署到您的电脑。

### 前提条件

- Docker Desktop 已安装并运行
- 端口 8086 和 3000 未被占用

### 部署完成后

1. 访问 InfluxDB：`http://localhost:8086`
   - 账号：admin / adminpassword
   - 组织：seeed，存储桶：recamera

2. 进入 **API Tokens** 复制令牌，后续配置需要

3. 访问 Grafana：`http://localhost:3000`
   - 默认账号：admin / admin

![架构图](gallery/architecture.svg)

### Troubleshooting

| 问题 | 解决方案 |
|------|----------|
| 端口被占用 | 关闭占用端口的程序，或在配置中修改端口 |
| Docker 无法启动 | 打开 Docker Desktop 应用 |
| 容器启动后停止 | 确保电脑有至少 4GB 可用内存 |

---
```

### Deployment Complete 部署完成区域

使用 H1 标题 `# Deployment Complete` 或 `# 部署完成` 标记整个部署流程结束后的内容。

**显示条件**：只有当所有 `required=true` 的步骤都完成后，此区域才会显示。

```markdown
# Deployment Complete

## 部署完成！

您的系统已就绪。

### 后续步骤

- [访问 Web 界面](http://localhost:8080)
- [查看 Wiki 文档](https://wiki.seeedstudio.com/...)

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 无法访问页面 | 检查服务是否正常运行 |
```

### 前端渲染逻辑

理解内容在前端的渲染位置，有助于合理组织 guide.md 的结构。

#### 渲染位置示意图

```
┌─────────────────────────────────────────────────────┐
│ [Preset 选择器]  云方案 | 私有云 | 边缘计算          │  ← ## Preset: 定义
├─────────────────────────────────────────────────────┤
│ Step 1: Deploy Backend                              │  ← ## Step 1: 定义
│ ┌─────────────────────────────────────────────────┐ │
│ │ [Target 选择器]  本机部署 | 远程部署             │ │  ← ### Target: 定义
│ ├─────────────────────────────────────────────────┤ │
│ │ 本机部署                                         │ │
│ │ 将后端服务部署到您的电脑。                        │ │
│ │                                                 │ │
│ │ 前提条件                                         │ │  ← ### 前提条件
│ │ • Docker Desktop 已安装并运行                    │ │
│ │                                                 │ │
│ │ 部署完成后                                       │ │  ← ### 部署完成后
│ │ 1. 访问 InfluxDB...                             │ │
│ │ 2. 复制 API Token...                            │ │
│ │                                                 │ │
│ │ [图片]                                          │ │  ← ![](gallery/...)
│ │                                                 │ │
│ │ [────────── 部署按钮 ──────────]                 │ │
│ │                                                 │ │
│ │ ┌─ Troubleshooting ─────────────────────────┐   │ │  ← ### Troubleshooting
│ │ │ | 问题 | 解决方案 |                        │   │ │     (单独提取到按钮下方)
│ │ │ | 端口被占用 | 关闭占用端口的程序 |         │   │ │
│ │ └───────────────────────────────────────────┘   │ │
│ │                                                 │ │
│ │ [日志区域 - 可折叠]                              │ │
│ └─────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│ Step 2: Configure Settings                          │  ← ## Step 2: 定义
│ ...                                                 │
├─────────────────────────────────────────────────────┤
│ ✓ 部署完成！                                        │  ← # Deployment Complete
│ 您的系统已就绪。                                     │     (仅当所有 required=true
│                                                     │      步骤完成后显示)
│ 后续步骤                                            │
│ [访问 Web 界面] [查看文档]                           │
└─────────────────────────────────────────────────────┘
```

#### Troubleshooting vs Deployment Complete

| 内容 | Markdown 格式 | 显示位置 | 显示时机 |
|------|---------------|----------|----------|
| **Troubleshooting** | `### Troubleshooting` (H3) | 每个步骤的部署按钮下方 | 始终显示 |
| **Deployment Complete** | `# Deployment Complete` (H1) | 页面最底部的成功卡片 | 所有必需步骤完成后 |

### 编写最佳实践

1. **步骤描述简洁明了**
   - 开头用一两句话说明这一步做什么
   - 使用有序列表列出操作步骤

2. **"部署完成后"放在 Troubleshooting 之前**
   ```markdown
   ### 部署完成后
   1. 访问 xxx
   2. 配置 xxx

   ### Troubleshooting
   | 问题 | 解决方案 |
   ```

3. **Troubleshooting 使用表格格式**
   ```markdown
   ### Troubleshooting

   | 问题 | 解决方案 |
   |------|----------|
   | 问题描述 | 解决方法 |
   ```

4. **图片放在相关说明附近**
   - 架构图放在步骤开头
   - 操作截图放在对应步骤旁边

5. **中英文结构保持一致**
   - guide.md 和 guide_zh.md 的 Preset/Step/Target ID 必须相同
   - 小标题数量和顺序保持一致

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

pre_checks:
  - type: docker_version
    min_version: "20.0"

post_deployment:
  open_browser: true
  url: "http://localhost:2125"
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

ssh:
  port: 22
  username: root

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

### 示例：智慧仓管方案

**solution.yaml**：

```yaml
version: "1.0"
id: smart_warehouse
name: Smart Warehouse Management
name_zh: 智慧仓管方案

intro:
  summary: Voice-controlled warehouse - zero learning curve
  summary_zh: 语音操控仓库管理——开口就会用

  description_file: description.md
  description_file_zh: description_zh.md
  cover_image: gallery/cover.png

  gallery:
    - type: image
      src: gallery/architecture.png
      caption: System architecture
      caption_zh: 系统架构图

  category: voice_ai
  tags: [mcp, voice, watcher, warehouse]

  presets:
    - id: sensecraft_cloud
      name: SenseCraft Cloud
      name_zh: 云方案
      badge: Recommended
      badge_zh: 推荐
      description: Quick setup with SenseCraft cloud
      description_zh: 连接 SenseCraft 云服务，快速部署

    - id: private_cloud
      name: Private Cloud
      name_zh: 私有云方案
      description: Self-hosted with external LLM API
      description_zh: 仓管系统本地部署，调用外部云 API

    - id: edge_computing
      name: Edge Computing
      name_zh: 边缘计算方案
      description: Pure LAN deployment
      description_zh: 纯局域网部署，数据不出厂区

  stats:
    difficulty: beginner
    estimated_time: 30min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

  partners:
    - name: Seeed Technology
      name_zh: 深圳矽递科技
      logo: gallery/partners/seeed.png
      regions: [广东省, 全国远程]
      regions_en: [Guangdong, Remote]
      contact: solutions@seeed.cc

deployment:
  guide_file: guide.md
  guide_file_zh: guide_zh.md
  selection_mode: sequential
```

**目录结构**：

```
solutions/smart_warehouse/
├── solution.yaml
├── description.md
├── description_zh.md
├── guide.md
├── guide_zh.md
├── gallery/
│   ├── cover.png
│   ├── architecture.png
│   ├── wiring.png
│   └── partners/
│       └── seeed.png
└── devices/
    ├── warehouse_local.yaml
    ├── warehouse_remote.yaml
    ├── xiaozhi_local.yaml
    ├── xiaozhi_remote.yaml
    └── mcp_bridge.yaml
```

---

## 最佳实践

### 1. 目录组织

- 所有 Markdown 文件直接放在方案根目录
- 图片统一放在 `gallery/` 目录
- 设备配置放在 `devices/` 目录
- 使用清晰的文件命名（如 `warehouse_local.yaml`、`warehouse_remote.yaml`）

### 2. Preset 设计原则

- **按部署方式分**：云方案、私有云、边缘计算
- **按规模分**：入门版、标准版、企业版
- **每个 preset 独立**：不同 preset 可以有完全不同的部署步骤
- **在 guide.md 中定义步骤**：而不是在 YAML 中

### 3. guide.md 编写规范

- 使用 `## Preset:` 定义套餐，`{#id}` 必须与 YAML 对应
- 使用 `## Step N:` 定义步骤，包含所需属性
- 使用 `### Target:` 定义部署目标（仅 docker_deploy 类型需要）
- 步骤说明简洁明了，使用有序列表
- 故障排除使用表格格式

### 4. 国际化规范

- 所有面向用户的字段都应提供 `_zh` 版本
- 文件名使用 `filename.md` / `filename_zh.md` 格式
- YAML 字段使用 `field` / `field_zh` 格式
- guide.md 和 guide_zh.md 结构必须一致（相同的 preset/step/target ID）

### 5. 测试清单

- [ ] 每个 preset id 在 YAML 和 guide.md 中都存在
- [ ] 每个 step 的 config 文件路径正确
- [ ] 所有引用的图片文件都存在
- [ ] 中英文版本结构一致
- [ ] `targets` 中只有一个 `default=true`

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目总体开发指南
- [文案编写规范](../.claude/skills/solution-copywriting/SKILL.md) - Markdown 内容编写规范
