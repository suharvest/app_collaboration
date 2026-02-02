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
│       ├── description.md      # 英文介绍
│       ├── description_zh.md   # 中文介绍
│       ├── guide.md            # 英文部署指南
│       ├── guide_zh.md         # 中文部署指南
│       ├── gallery/            # 图片资源
│       └── devices/            # 设备部署配置
├── tests/                       # 测试
│   ├── unit/                   # 单元测试
│   └── integration/            # 集成测试
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
    ├── solution.yaml           # 方案配置（必须）
    ├── description.md          # 英文介绍（必须）
    ├── description_zh.md       # 中文介绍（必须）
    ├── guide.md                # 英文部署指南（必须）
    ├── guide_zh.md             # 中文部署指南（必须）
    ├── gallery/                # 图片资源
    │   ├── cover.png           # 封面图
    │   └── architecture.png    # 架构图
    └── devices/                # 设备部署配置
        └── docker-compose.yaml
```

#### 2. 编写 solution.yaml

部署步骤定义在 `guide.md` 中，YAML 只需配置元数据和预设信息：

```yaml
version: "1.0"
id: your_solution_id
name: Solution Name
name_zh: 方案名称

intro:
  summary: One-line description
  summary_zh: 一句话描述

  description_file: description.md
  description_file_zh: description_zh.md
  cover_image: gallery/cover.png

  category: voice_ai  # voice_ai | sensing | automation
  tags: [iot, watcher]

  # 设备目录（介绍页显示的设备信息）
  device_catalog:
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: gallery/watcher.png
      product_url: https://www.seeedstudio.com/...

  # 预设套餐（具体步骤定义在 guide.md）
  presets:
    - id: default
      name: Standard Deployment
      name_zh: 标准部署
      description: Quick setup with cloud services
      description_zh: 使用云服务快速部署
      architecture_image: gallery/architecture.png
      device_groups:
        - id: main_device
          name: Main Device
          name_zh: 主设备
          type: single
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher

  stats:
    difficulty: beginner  # beginner | intermediate | advanced
    estimated_time: 30min

deployment:
  guide_file: guide.md
  guide_file_zh: guide_zh.md
  selection_mode: sequential
```

#### 3. 部署器类型

在 `guide.md` 中使用 `type=xxx` 定义步骤类型：

| 类型 | 说明 | 配置要求 |
|------|------|----------|
| `docker_deploy` | Docker 容器部署（支持本地/远程） | `config=devices/xxx.yaml` |
| `docker_local` | 本地 Docker 部署 | `config=devices/xxx.yaml` |
| `docker_remote` | 远程 Docker 部署 | `config=devices/xxx.yaml` |
| `esp32_usb` | ESP32 USB 烧录 | `config=devices/xxx.yaml` |
| `himax_usb` | Himax WE2 烧录 | `config=devices/xxx.yaml` |
| `recamera_cpp` | reCamera C++ 部署 | `config=devices/xxx.yaml` |
| `recamera_nodered` | reCamera Node-RED 部署 | `config=devices/xxx.yaml` |
| `ssh_deb` | SSH + DEB 包安装 | `config=devices/xxx.yaml` |
| `manual` | 手动步骤 | 无需 config |
| `script` | 脚本执行 | `config=devices/xxx.yaml` |
| `preview` | 预览步骤（无部署） | 无需 config |

#### 4. guide.md 示例

部署步骤定义在 guide.md 中：

```markdown
## Preset: Cloud Version {#cloud}

使用云服务快速部署。

## Step 1: 配置设备 {#sensecraft type=manual required=true}

按照以下步骤配置设备...

## Step 2: 部署服务 {#warehouse type=docker_deploy required=true config=devices/docker-compose.yaml}

### Target: 本机部署 {#warehouse_local default=true}

在本机部署 Docker 容器。

### Target: 远程部署 {#warehouse_remote}

部署到远程服务器。
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
| `/api/health` | GET | 健康检查 |
| `/api/solutions?lang=zh` | GET | 获取方案列表 |
| `/api/solutions/{id}?lang=zh` | GET | 获取方案详情 |
| `/api/solutions/{id}/deployment?lang=zh` | GET | 获取部署信息 |
| `/api/solutions/{id}/assets/{path}` | GET | 获取静态资源 |
| `/api/devices/scan-mdns` | GET | mDNS 局域网设备扫描 |
| `/api/docker-devices/local/check` | GET | 检查本地 Docker 状态 |
| `/api/docker-devices/local/managed-apps` | GET | 获取已部署应用 |
| `/api/deployments/start` | POST | 开始部署 |
| `/ws/deployments/{id}` | WS | 部署日志 WebSocket |

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
