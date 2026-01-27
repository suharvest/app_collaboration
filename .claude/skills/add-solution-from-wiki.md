# Skill: 从 Wiki 创建新方案

## 触发条件

当用户提供 Wiki URL 并要求创建新方案时使用此 skill。

## 执行步骤

### 1. 获取 Wiki 内容

```
使用 WebFetch 或 mcp__firecrawl__firecrawl_scrape 获取 Wiki 页面内容
```

### 2. 分析 Wiki 结构

从 Wiki 中提取：
- 方案名称（中英文）
- 功能介绍
- 所需硬件设备
- 部署步骤（区分不同套餐的步骤）
- 架构图/截图

### 3. 创建目录结构

```bash
solutions/[solution_id]/
├── solution.yaml
├── intro/
│   ├── description.md
│   ├── description_zh.md
│   └── gallery/
└── deploy/
    ├── guide.md
    ├── guide_zh.md
    └── sections/
```

### 4. 生成 solution.yaml

#### 关键字段映射

| Wiki 内容 | YAML 字段 |
|----------|----------|
| 标题 | `name` / `name_zh` |
| 简介第一段 | `intro.summary` / `intro.summary_zh` |
| 硬件清单 | `intro.device_catalog` |
| 难度说明 | `intro.stats.difficulty` |
| 预计时间 | `intro.stats.estimated_time` |
| 部署套餐/模式 | `intro.presets` |
| 部署步骤 | `intro.presets[].devices` |

#### 新架构：每个 preset 包含完整的 devices 列表

```yaml
version: "1.0"
id: solution_id
name: Solution Name
name_zh: 方案名称

intro:
  summary: One-line description
  summary_zh: 一句话描述

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md
  cover_image: intro/gallery/cover.png

  category: voice_ai
  tags: [tag1, tag2]

  # 设备目录
  device_catalog:
    device1:
      name: Device Name
      name_zh: 设备名称
      image: intro/gallery/device1.png
      product_url: https://...

  # 预设套餐（每个 preset 包含完整的 devices 列表）
  presets:
    - id: preset_a
      name: Preset A
      name_zh: 套餐 A
      description: For scenario A
      description_zh: 适用于场景 A
      badge: Recommended
      badge_zh: 推荐
      device_groups:
        - id: main_device
          name: Main Device
          type: single
          options:
            - device_ref: device1
          default: device1
      architecture_image: intro/gallery/architecture_a.png
      links:
        wiki: https://wiki.seeedstudio.com/...
      # 该套餐的完整部署步骤
      devices:
        - id: step1
          name: Step 1
          name_zh: 步骤 1
          type: manual
          required: true
          section:
            title: Step 1 Title
            title_zh: 步骤 1 标题
            description_file: deploy/sections/step1.md
            description_file_zh: deploy/sections/step1_zh.md
        - id: step2
          name: Step 2
          name_zh: 步骤 2
          type: docker_deploy
          required: true
          config_file: devices/service.yaml
          section:
            title: Step 2 Title
            title_zh: 步骤 2 标题
          targets:
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/service_local.yaml
              section:
                description_file: deploy/sections/step2_local.md
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/service_remote.yaml
              section:
                description_file: deploy/sections/step2_remote.md

    - id: preset_b
      name: Preset B
      name_zh: 套餐 B
      description: For scenario B
      description_zh: 适用于场景 B
      device_groups:
        - id: main_device
          type: single
          options:
            - device_ref: device1
          default: device1
      # 不同套餐可以有不同的部署步骤
      devices:
        - id: step1
          name: Step 1
          name_zh: 步骤 1
          type: manual
          required: true
          section:
            title: Step 1 Title
            title_zh: 步骤 1 标题
            description_file: deploy/sections/step1.md
            description_file_zh: deploy/sections/step1_zh.md
        - id: step3_special
          name: Step 3 (Preset B only)
          name_zh: 步骤 3（套餐 B 专属）
          type: esp32_usb
          required: true
          config_file: devices/esp32.yaml
          section:
            title: Flash Firmware
            title_zh: 烧录固件
            description_file: deploy/sections/step3.md

  stats:
    difficulty: beginner  # beginner | intermediate | advanced
    estimated_time: 30min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

# 部署配置（设备已移至 preset.devices）
deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  selection_mode: sequential

  # 设备列表已移至各 preset.devices 中
  devices: []
  order: []

  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps:
      - title: Access Dashboard
        title_zh: 访问仪表板
        action: open_url
        url: http://localhost:5173
```

### 5. 转换 Markdown 内容

#### Wiki → 介绍页 (description.md)

**删除**:
- H1 标题（页面已有）
- 目录导航
- 硬件购买链接（移到 device_catalog）
- 系统要求/前置条件（移到 deploy/guide.md）

**保留**:
- 功能特点（从 H2 开始）
- 使用场景
- 示例表格

**转换示例**:

Wiki 原文:
```markdown
# SenseCAP Watcher MCP Integration

## Introduction
This guide shows how to...

## Requirements
- Docker installed
- Python 3.8+

## Features
- Voice control
- Real-time sync
```

转换后 (description.md):
```markdown
## Features

- **Voice Control** - Hands-free operation
- **Real-time Sync** - Instant data updates
```

转换后 (guide.md):
```markdown
## 部署前准备

确保已安装:
- Docker
- Python 3.8+
```

#### Wiki → 部署页 (guide.md / sections/)

**简化原则**:
- 一键部署：只保留部署后验证步骤
- 手动步骤：保留必要的用户操作说明
- 删除 git clone、docker 命令（系统自动执行）

### 6. 下载图片资源

```bash
# 从 Wiki 下载图片到 gallery 目录
curl -o intro/gallery/image.png "wiki_image_url"
```

### 7. 验证配置

```bash
# 重启服务器
./dev.sh

# 检查方案是否加载
curl http://localhost:3260/api/solutions
```

## 输出格式

完成后告知用户：
1. 创建的文件列表
2. 需要手动补充的内容（如图片）
3. 访问地址

## 示例对话

**用户**: 帮我把这个 Wiki 页面转成方案 https://wiki.seeedstudio.com/xxx

**助手**:
1. 获取 Wiki 内容
2. 创建 solutions/xxx/ 目录
3. 生成 solution.yaml（包含 preset.devices 结构）
4. 转换 markdown 内容
5. 提示用户补充图片

## 重要提醒

- **不要使用 show_when**：已废弃的条件显示方式
- **每个 preset 完整定义 devices**：不同套餐可以有完全不同的部署步骤
- **deployment.devices 保持为空**：设备定义已移至 preset.devices
- **参考文档**：`docs/solution-configuration-guide.md`
