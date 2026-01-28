# SenseCraft Solution

IoT 解决方案部署平台，用于展示和一键部署 Seeed Studio 硬件产品方案。

## 功能特点

- **方案展示**: 浏览、搜索 IoT 解决方案，查看详细介绍和所需设备
- **一键部署**: 自动完成固件烧录、Docker 容器部署、SSH 远程执行等操作
- **设备支持**: ESP32 固件烧录、Himax WE2 AI 芯片编程、Docker 容器管理
- **实时反馈**: WebSocket 实时日志、传感器/摄像头预览
- **多语言**: 中英文双语支持
- **跨平台**: Web 应用 + Tauri 桌面应用 (macOS/Linux/Windows)

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vite + Vanilla JS + Tailwind CSS |
| 后端 | Python FastAPI + Uvicorn |
| 桌面 | Tauri 2.0 (Rust) + PyInstaller Sidecar |
| 数据 | YAML 配置 + Markdown 内容 |

## 目录结构

```
app_collaboration/
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── modules/            # 核心模块 (api, i18n, router)
│   │   └── pages/              # 页面组件
│   └── design-system/          # 设计系统
├── provisioning_station/       # 后端服务
│   ├── routers/                # API 路由
│   ├── services/               # 业务逻辑
│   └── deployers/              # 部署器 (ESP32, Docker, SSH...)
├── solutions/                  # 方案配置目录
│   └── [solution_id]/
│       ├── solution.yaml       # 方案配置
│       ├── intro/              # 介绍页内容
│       └── deploy/             # 部署页内容
├── src-tauri/                  # Tauri 桌面应用
│   ├── src/main.rs
│   ├── tauri.conf.json
│   └── binaries/               # Sidecar 可执行文件
├── scripts/                    # 构建脚本
├── dev.sh                      # 开发启动脚本
└── run.sh                      # 生产启动脚本
```

---

## 部署方式

### 方式一: Web 开发模式

适用于本地开发和调试。

#### 环境要求

- Python 3.11+
- Node.js 16+
- [uv](https://github.com/astral-sh/uv) (Python 包管理器)

#### 安装依赖

```bash
# Python 依赖
uv sync

# 前端依赖
cd frontend && npm install && cd ..
```

#### 启动开发服务器

```bash
./dev.sh
```

- 前端: http://localhost:5173 (Vite 热重载)
- 后端: http://localhost:3260 (API 服务)
- 前端自动代理 `/api/*` 请求到后端

#### 生产模式

```bash
./run.sh
```

前端构建后由后端静态服务，访问 http://localhost:3260

---

### 方式二: Tauri 桌面应用

打包为独立桌面应用，适用于分发给终端用户。

#### 额外环境要求

- Rust 工具链 ([rustup.rs](https://rustup.rs/))
- Tauri CLI: `cargo install tauri-cli`

#### 构建步骤

**1. 构建 Python Sidecar**

```bash
uv run --group build python scripts/build-sidecar.py
```

输出: `src-tauri/binaries/provisioning-station-{target-triple}`

**2. 构建 Tauri 应用**

```bash
cd src-tauri
cargo tauri build
```

输出位置:
- macOS: `src-tauri/target/release/bundle/dmg/SenseCraft Solution_*.dmg`
- Linux: `src-tauri/target/release/bundle/deb/*.deb`
- Windows: `src-tauri/target/release/bundle/msi/*.msi`

#### 开发模式

```bash
cd src-tauri
cargo tauri dev
```

---

## 新增方案

> 📖 **详细配置指南**: [docs/solution-configuration-guide.md](docs/solution-configuration-guide.md)

### 快速开始

#### 1. 创建目录结构

```bash
solutions/
└── your_solution_id/
    ├── solution.yaml           # 必须
    ├── intro/
    │   ├── description.md      # 英文介绍
    │   ├── description_zh.md   # 中文介绍
    │   └── gallery/
    │       └── cover.png       # 封面图
    ├── deploy/
    │   ├── guide.md            # 英文部署指南
    │   ├── guide_zh.md         # 中文部署指南
    │   └── sections/           # 部署步骤说明
    │       ├── step1.md
    │       └── step1_zh.md
    └── devices/                # 设备配置
        └── device.yaml
```

#### 2. 编写 solution.yaml

每个 **preset（预设套餐）** 包含完整的 **devices（部署步骤）** 列表：

```yaml
version: "1.0"
id: your_solution_id
name: Solution Name
name_zh: 方案名称

intro:
  summary: One-line description
  summary_zh: 一句话描述

  description_file: intro/description.md
  description_file_zh: intro/description_zh.md
  cover_image: intro/gallery/cover.png

  category: voice_ai  # voice_ai | sensing | automation
  tags: [iot, watcher]

  # 设备目录
  device_catalog:
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: intro/gallery/watcher.png
      product_url: https://www.seeedstudio.com/...

  # 预设套餐（每个 preset 包含完整的部署步骤）
  presets:
    - id: default
      name: Standard Deployment
      name_zh: 标准部署
      device_groups:
        - id: main_device
          name: Main Device
          type: single
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher
      # 该套餐的部署步骤
      devices:
        - id: step1
          name: Flash Firmware
          name_zh: 烧录固件
          type: esp32_usb
          required: true
          config_file: devices/device.yaml
          section:
            title: Step 1
            title_zh: 第一步
            description_file: deploy/sections/step1.md
            description_file_zh: deploy/sections/step1_zh.md
        - id: step2
          name: Configure Device
          name_zh: 配置设备
          type: manual
          required: true
          section:
            title: Step 2
            title_zh: 第二步
            description_file: deploy/sections/step2.md

  stats:
    difficulty: beginner  # beginner | intermediate | advanced
    estimated_time: 30min

# 部署配置（设备已移至 preset.devices）
deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  devices: []   # 保持为空
  order: []     # 保持为空
  post_deployment:
    success_message_file: deploy/success.md
```

#### 3. 部署器类型

| 类型 | 说明 | 配置要求 |
|------|------|----------|
| `esp32_usb` | ESP32 USB 烧录 | `config_file` 指定固件配置 |
| `himax_usb` | Himax WE2 烧录 | `config_file` 指定固件配置 |
| `docker_deploy` | Docker 容器部署 | `config_file` 或 `targets` |
| `manual` | 手动步骤 | 仅需 `section` |
| `preview` | 实时预览 | `config_file` 指定视频/MQTT |

#### 4. 多套餐支持

不同 preset 可以有不同的部署步骤：

```yaml
intro:
  presets:
    - id: cloud
      name: Cloud Version
      devices:
        - id: step1
        - id: cloud_config  # 云版本特有

    - id: edge
      name: Edge Version
      devices:
        - id: step1
        - id: edge_setup    # 边缘版本特有
        - id: local_llm     # 边缘版本特有
```

### 相关文档

| 文档 | 说明 |
|------|------|
| [配置指南](docs/solution-configuration-guide.md) | solution.yaml 完整配置说明 |
| [从 Wiki 创建](.claude/skills/add-solution-from-wiki.md) | 从 Wiki 页面生成方案 |
| [文案规范](.claude/skills/solution-copywriting/SKILL.md) | 介绍页/部署页文案标准 |

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/solutions?lang=zh` | GET | 获取方案列表 |
| `/api/solutions/{id}?lang=zh` | GET | 获取方案详情 |
| `/api/solutions/{id}/deployment?lang=zh` | GET | 获取部署信息 |
| `/api/solutions/{id}/assets/{path}` | GET | 获取静态资源 |
| `/api/deployments` | POST | 开始部署 |
| `/api/deployments/{id}/logs` | WS | 部署日志流 |
| `/api/devices` | GET | 获取已连接设备 |

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `PS_SOLUTIONS_DIR` | 方案目录路径 | `./solutions` |
| `PS_DEBUG` | 调试模式 | `false` |

---

## 常见问题

**Q: 页面显示旧内容？**

```bash
rm -rf frontend/dist
./dev.sh
```

**Q: ESP32 烧录失败？**

确保使用正确的 Python 环境 (esptool 版本需匹配):

```bash
export IDF_PYTHON_ENV_PATH=/path/to/python_env
```

**Q: Tauri 构建失败？**

确保先构建 Sidecar:

```bash
uv run --group build python scripts/build-sidecar.py
```

---

## License

MIT
