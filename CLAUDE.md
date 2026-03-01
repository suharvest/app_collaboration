# SenseCraft Solution 开发指南

## 项目概述

IoT 解决方案一键部署平台。用户在 Web/桌面端选方案 → 选预设 → 连接设备 → 一键部署。
技术栈：Vite + Vanilla JS 前端 | Python FastAPI 后端 | Tauri 桌面壳 | YAML + Markdown 方案配置。

---

## 核心架构

```
用户选方案 → solution.yaml（介绍/设备/预设）
         → guide.md（部署步骤定义 + 文档）
         → devices/*.yaml（每步的设备配置）
                ↓
后端解析 markdown_parser → 提取 Step/Target 定义
       → step_registry → 根据 device_type 生成部署步骤
       → deployment_engine → 调度 DEPLOYER_REGISTRY 中的 deployer 执行
                ↓
前端 deploy/ 模块 → WebSocket 实时显示进度
```

### 关键设计模式

- **Deployer 自注册**：`deployers/__init__.py` 自动扫描包内所有模块，收集 `BaseDeployer` 子类到 `DEPLOYER_REGISTRY`，按 `device_type` 索引。新增部署类型只需创建新文件。
- **ui_traits**：每个 Deployer 声明 `ui_traits` dict（connection/auto_deploy/renderer/has_targets 等），前端据此动态渲染 UI。
- **guide.md 驱动部署**：部署步骤不在 YAML 中定义，而在 guide.md 的 H2 header 元数据中：`## Step N: Title {#id type=xxx config=devices/xxx.yaml}`。
- **设备全局目录**：`devices/catalog.yaml` 定义所有硬件设备，solution.yaml 的 `device_catalog` 可引用或覆盖。

---

## 项目结构（完整）

```
app_collaboration/
├── frontend/                          # 前端 (Vite + Vanilla JS + Tailwind)
│   ├── src/
│   │   ├── main.js                    # 入口：路由注册、导航、i18n 初始化
│   │   ├── main.css                   # 全局样式
│   │   ├── modules/                   # 核心模块
│   │   │   ├── api.js                 # API 调用、后端端口发现、WebSocket
│   │   │   ├── i18n.js                # 国际化 (en/zh)
│   │   │   ├── router.js              # hash 路由
│   │   │   ├── toast.js               # 通知提示
│   │   │   ├── preview.js             # 视频预览（RTSP proxy/HLS）
│   │   │   ├── serial-camera.js       # 串口摄像头 WebSocket 客户端
│   │   │   ├── overlay-renderers.js   # AI 检测框渲染
│   │   │   ├── updater.js             # 自动更新（Tauri）
│   │   │   ├── utils.js               # 通用工具函数
│   │   │   └── __tests__/             # 模块测试 (Vitest)
│   │   └── pages/                     # 页面
│   │       ├── solutions.js           # 方案列表页
│   │       ├── solution-detail.js     # 方案详情页（介绍/设备/预设选择）
│   │       ├── deploy.js              # 部署页入口（re-export）
│   │       ├── deploy/                # 部署页模块化拆分
│   │       │   ├── index.js           # 部署主逻辑：加载方案、渲染步骤
│   │       │   ├── state.js           # 部署状态管理
│   │       │   ├── handlers.js        # 按钮/事件处理
│   │       │   ├── devices.js         # 设备连接 UI
│   │       │   ├── docker.js          # Docker 设备特殊处理
│   │       │   ├── renderers.js       # 步骤卡片渲染
│   │       │   ├── ui-updates.js      # UI 状态更新
│   │       │   ├── websocket.js       # 部署 WebSocket 管理
│   │       │   ├── preview.js         # 部署中的预览面板
│   │       │   ├── serial-camera-handler.js  # 串口摄像头步骤处理
│   │       │   ├── face-database-panel.js    # 人脸数据库面板
│   │       │   ├── utils.js           # 部署页工具函数
│   │       │   └── __tests__/         # 部署页测试
│   │       ├── deployments.js         # 部署历史页
│   │       ├── devices.js             # 已连接设备管理页
│   │       ├── solution-management.js # 方案管理页（导入/导出）
│   │       └── settings.js            # 设置页
│   ├── design-system/
│   │   └── components.css             # 设计系统组件样式
│   └── public/                        # 静态资源
│
├── provisioning_station/              # 后端 (FastAPI)
│   ├── main.py                        # FastAPI app、路由注册、生命周期
│   ├── config.py                      # Settings（端口/路径/语言，env_prefix=PS_）
│   ├── __main__.py                    # uvicorn 启动入口
│   │
│   ├── routers/                       # API 路由
│   │   ├── solutions.py              # /api/solutions — 方案 CRUD
│   │   ├── devices.py                # /api/devices — USB/串口设备检测
│   │   ├── docker_devices.py         # /api/docker-devices — Docker 状态/应用管理
│   │   ├── deployments.py            # /api/deployments — 启动/取消部署
│   │   ├── websocket.py              # /ws/deployments — 实时日志 WebSocket
│   │   ├── device_management.py      # /api/device-management — 已部署设备管理
│   │   ├── preview.py                # /api/preview — 视频流代理
│   │   ├── serial_camera.py          # /api/serial-camera — 串口摄像头 WebSocket
│   │   ├── restore.py                # /api/restore — 设备恢复出厂
│   │   └── versions.py               # /api/versions — 版本/更新检查
│   │
│   ├── services/                      # 业务逻辑
│   │   ├── solution_manager.py       # 方案加载/解析（YAML + Markdown）
│   │   ├── markdown_parser.py        # guide.md 解析：Step/Target/Preset 提取
│   │   ├── deployment_engine.py      # 部署编排：调度 deployer、管理状态
│   │   ├── deployment_history.py     # 部署历史记录
│   │   ├── device_detector.py        # USB/串口设备检测
│   │   ├── docker_device_manager.py  # Docker 容器管理
│   │   ├── mdns_scanner.py           # mDNS 局域网设备扫描
│   │   ├── pre_check_validator.py    # 部署前检查（Docker/磁盘/端口）
│   │   ├── remote_pre_check.py       # 远程设备预检查（SSH）
│   │   ├── stream_proxy.py           # RTSP → WebSocket 视频流代理
│   │   ├── serial_camera_service.py  # 串口摄像头 WebSocket 服务
│   │   ├── serial_crud_service.py    # 串口设备 CRUD（人脸数据库）
│   │   ├── serial_port_manager.py    # 串口端口管理
│   │   ├── face_enroll_logic.py      # 人脸注册业务逻辑
│   │   ├── mqtt_bridge.py            # MQTT 桥接（设备消息转发）
│   │   ├── kiosk_manager.py          # Kiosk 模式管理
│   │   ├── localized.py              # 多语言字段处理
│   │   ├── restore_manager.py        # 设备恢复管理
│   │   ├── update_manager.py         # 应用更新管理
│   │   └── version_manager.py        # 版本管理
│   │
│   ├── deployers/                     # 部署器（自注册模式）
│   │   ├── __init__.py               # 自动扫描 → DEPLOYER_REGISTRY
│   │   ├── base.py                   # BaseDeployer ABC（device_type/ui_traits/steps/deploy）
│   │   ├── docker_deployer.py        # docker_local: docker compose up
│   │   ├── docker_remote_deployer.py # docker_remote: SSH + docker compose
│   │   ├── esp32_deployer.py         # esp32_usb: esptool 烧录
│   │   ├── himax_deployer.py         # himax_usb: xmodem 烧录
│   │   ├── recamera_cpp_deployer.py  # recamera_cpp: SSH + deb 包
│   │   ├── recamera_nodered_deployer.py # recamera_nodered: SSH + Node-RED flow
│   │   ├── ssh_deployer.py           # ssh_deb: SSH + deb 包安装
│   │   ├── ssh_binary_deployer.py    # ssh_binary: SSH + 二进制部署
│   │   ├── script_deployer.py        # script: 本地脚本执行
│   │   ├── manual_deployer.py        # manual: 手动步骤提示
│   │   ├── preview_deployer.py       # preview: 无操作，仅显示预览
│   │   ├── serial_camera_deployer.py # serial_camera: 串口摄像头预览
│   │   ├── nodered_deployer.py       # Node-RED 基类
│   │   ├── ha_integration_deployer.py # Home Assistant 集成
│   │   └── action_executor.py        # actions.before/after 执行器
│   │
│   ├── models/                        # 数据模型 (Pydantic)
│   │   ├── solution.py               # Solution/Preset/DeviceGroup/DeviceCatalog
│   │   ├── device.py                 # DeviceConfig（所有设备类型配置的联合体）
│   │   ├── deployment.py             # Deployment/DeploymentStatus
│   │   ├── docker_device.py          # Docker 设备模型
│   │   ├── api.py                    # API 请求/响应模型
│   │   ├── websocket.py              # WebSocket 消息模型
│   │   ├── version.py                # 版本/部署记录模型
│   │   └── kiosk.py                  # Kiosk 模式模型
│   │
│   ├── utils/                         # 工具
│   │   ├── step_registry.py          # 根据 deployer.steps + device config 生成步骤
│   │   ├── template.py               # 模板变量替换
│   │   ├── compose_labels.py         # Docker Compose label 管理
│   │   └── recamera_ssh.py           # reCamera SSH 工具
│   │
│   └── factory_firmware/              # 出厂固件
│       ├── esp32/                     # ESP32 出厂固件
│       ├── himax/                     # Himax 出厂固件
│       └── restore_config.yaml        # 恢复配置
│
├── solutions/                         # 方案目录（每个子目录一个方案）
│   ├── smart_warehouse/              # 智能仓库
│   ├── smart_space_assistant/        # 智慧空间助手
│   ├── smart_retail_voice_ai/        # 智慧零售语音 AI
│   ├── smart_hvac_control/           # 智能暖通控制
│   ├── recamera_heatmap_grafana/     # reCamera 热力图 + Grafana
│   ├── recamera_ecosystem/           # reCamera 生态方案
│   └── indoor_positioning_ble_lorawan/ # 室内定位 (BLE + LoRaWAN)
│   # 每个方案的标准结构：
│   #   solution.yaml    — 方案元数据/设备/预设
│   #   description.md   — 英文介绍
│   #   description_zh.md — 中文介绍
│   #   guide.md         — 英文部署指南（含 Step 定义）
│   #   guide_zh.md      — 中文部署指南
│   #   devices/         — 设备配置 YAML
│   #   gallery/         — 图片资源
│   #   docker/          — Docker Compose 等（可选）
│   #   packages/        — deb 包/模型文件（可选）
│
├── devices/
│   └── catalog.yaml                   # 全局设备目录（所有 Seeed 硬件）
│
├── shared/
│   └── constants.py                   # 前后端共享常量（端口/语言/设备类型/WS消息类型）
│
├── tests/
│   ├── unit/                          # 单元测试（不需要后端运行）
│   ├── integration/                   # 集成测试 + API 契约测试（需后端运行）
│   ├── e2e/                           # 端到端测试（实际设备）
│   └── fixtures/                      # 测试固件
│
├── src-tauri/                         # Tauri 桌面壳 (Rust)
│   ├── src/main.rs                    # Rust 主程序（sidecar 管理/端口注入）
│   ├── tauri.conf.json                # Tauri 配置
│   ├── capabilities/default.json      # 权限
│   ├── binaries/                      # Sidecar（PyInstaller 打包的后端）
│   ├── icons/                         # 应用图标
│   └── deb-files/                     # Linux deb 打包资源
│
├── pyinstaller/                       # PyInstaller 打包配置
├── scripts/                           # 构建/迁移脚本
│   ├── build-sidecar.py              # Sidecar 构建
│   ├── build-desktop.sh              # 桌面应用构建
│   └── ...                           # 其他迁移脚本
│
├── .github/workflows/                 # CI/CD
│   ├── release.yml                    # 发布流程
│   └── test.yml                       # 测试流程
│
├── .claude/skills/                    # Claude 技能
├── data/                              # 运行时数据（缓存/日志）
├── dev.sh                             # 开发启动脚本
├── pyproject.toml                     # Python 项目配置 (uv)
└── .pre-commit-config.yaml            # Pre-commit hooks
```

---

## 快速定位指南

| 要修改什么 | 找哪个文件 |
|-----------|-----------|
| 方案介绍/设备/预设 | `solutions/{id}/solution.yaml` |
| 部署步骤定义 | `solutions/{id}/guide.md` 的 `## Step:` H2 标题 |
| 设备配置（端口/固件/Docker等） | `solutions/{id}/devices/*.yaml` |
| 新增部署器类型 | `provisioning_station/deployers/` 创建新文件 |
| API 端点 | `provisioning_station/routers/*.py` |
| 方案加载/解析逻辑 | `provisioning_station/services/solution_manager.py` |
| guide.md 解析规则 | `provisioning_station/services/markdown_parser.py` |
| 部署执行流程 | `provisioning_station/services/deployment_engine.py` |
| 前端部署页交互 | `frontend/src/pages/deploy/` 目录 |
| 前端 API 调用 | `frontend/src/modules/api.js` |
| 翻译文本 | `frontend/src/modules/i18n.js` |
| 全局设备目录 | `devices/catalog.yaml` |
| 共享常量 | `shared/constants.py` |
| 设计系统样式 | `frontend/design-system/components.css` |

---

## 设备类型与 Deployer 映射

| device_type | Deployer 文件 | 连接方式 | 说明 |
|-------------|--------------|---------|------|
| `docker_local` | docker_deployer.py | 本地 Docker | docker compose up |
| `docker_remote` | docker_remote_deployer.py | SSH | 远程 Docker 部署 |
| `docker_deploy` | — (guide.md 中用) | — | 统一写法，Target 区分 local/remote |
| `esp32_usb` | esp32_deployer.py | USB 串口 | esptool 烧录 |
| `himax_usb` | himax_deployer.py | USB 串口 | xmodem 烧录 |
| `recamera_cpp` | recamera_cpp_deployer.py | SSH | deb 包 + 模型部署 |
| `recamera_nodered` | recamera_nodered_deployer.py | SSH | Node-RED flow 部署 |
| `ssh_deb` | ssh_deployer.py | SSH | deb 包安装 |
| `script` | script_deployer.py | 本地 | 本地脚本执行 |
| `manual` | manual_deployer.py | 无 | 手动步骤提示 |
| `preview` | preview_deployer.py | 无 | 仅显示预览 |
| `serial_camera` | serial_camera_deployer.py | USB 串口 | 串口摄像头预览 |
| `ha_integration` | ha_integration_deployer.py | HTTP | Home Assistant 集成 |

**注意**: YAML 配置中用 `docker_local`/`docker_remote`；guide.md 中统一写 `docker_deploy` + `### Target:` 区分。

---

## guide.md Step/Target 语法

```markdown
## Preset: Preset Name {#preset_id}
## 套餐: 套餐名称 {#preset_id}

| Device | Purpose |
|--------|---------|
| ... | ... |

## Step 1: Step Title {#step_id type=docker_deploy required=true config=devices/default.yaml}

Step description markdown...

### Target: Local {#target_local type=local config=devices/local.yaml default=true}
### Target: Remote {#target_remote type=remote config=devices/remote.yaml}

## Step 2: Flash Firmware {#step_id type=esp32_usb required=true config=devices/firmware.yaml}

# Deployment Complete
# 部署完成

Post-deployment instructions...
```

---

## 文案编写规范

创建/修改 `solutions/` 下文档前，**必须先读取** `.claude/skills/solution-copywriting/SKILL.md`。

---

## 方案 solution.yaml 模板

```yaml
version: "1.0"
id: your_solution_id          # ^[a-z][a-z0-9_]*$
name: Solution Name
name_zh: 方案名称

intro:
  summary: One-line description
  summary_zh: 一句话描述
  description_file: description.md
  description_file_zh: description_zh.md
  cover_image: gallery/cover.png
  category: voice_ai
  tags: [iot, watcher]

  device_catalog:              # 本方案用到的设备（可引用 devices/catalog.yaml）
    device_key:
      name: Device Name
      name_zh: 设备名称
      product_url: https://...

  presets:                     # 部署预设
    - id: preset_id
      name: Preset Name
      name_zh: 预设名称
      device_groups:
        - id: group_id
          name: Group Name
          type: single         # single | multiple | quantity
          options:
            - device_ref: device_key
          default: device_key

  stats:
    difficulty: beginner       # beginner | intermediate | advanced
    estimated_time: 30min
  links:
    wiki: https://...

deployment:
  guide_file: guide.md
  guide_file_zh: guide_zh.md
```

---

## 开发命令

```bash
# 启动开发服务器（前端 :5173 + 后端 :3260）
./dev.sh
```

---

## 打包与发布

### 架构

```
PyInstaller 打包 Python 后端 → sidecar 可执行文件
                                    ↓
Tauri 打包 (Rust 壳 + 前端 dist + sidecar + solutions/) → 桌面安装包
```

- **Sidecar 模式**：Python 后端通过 PyInstaller 打包为独立可执行文件（含 `_internal/` 依赖目录）
- **动态端口**：Tauri (Rust) 用 portpicker 选空闲端口，通过 `window.__BACKEND_PORT__` 注入前端
- **Solutions 资源**：通过 Tauri resources 打包到安装包内（macOS: `Contents/Resources/_up_/solutions/`）
- **自动更新**：Tauri updater 插件，endpoint 指向 GitHub Release 的 `latest.json`

### 本地构建

```bash
# 一键构建（推荐）
./scripts/build-desktop.sh --build

# 分步构建：
# 1. 构建 Python Sidecar（输出到 src-tauri/binaries/）
uv run --group build python scripts/build-sidecar.py

# 2. 构建 Tauri 桌面应用
cd src-tauri && cargo tauri build

# 开发模式（带热重载）
./scripts/build-desktop.sh --dev
# 或
cd src-tauri && cargo tauri dev

# 跳过 sidecar 重建（已有时）
./scripts/build-desktop.sh --build --skip-sidecar
```

### 构建产物

| 平台 | 格式 | 路径 |
|------|------|------|
| macOS (Apple Silicon) | `.dmg` / `.app` | `src-tauri/target/release/bundle/dmg/` |
| Windows (x64) | `.exe` (NSIS) | `src-tauri/target/release/bundle/nsis/` |
| Linux (ARM64) | `.deb` | `src-tauri/target/release/bundle/deb/` |

### CI 发布流程 (`.github/workflows/release.yml`)

触发：push tag `v*` 或手动 workflow_dispatch

```
pre-release-tests → build-sidecar (3 平台并行) → build-tauri (3 平台并行) → GitHub Release (draft)
```

| 阶段 | 说明 |
|------|------|
| pre-release-tests | 跑全量 pytest（含 unit + integration） |
| build-sidecar | PyInstaller 打包，矩阵：windows-latest / macos-latest / ubuntu-22.04-arm |
| build-tauri | 下载 sidecar artifact → 前端 build → cargo tauri build → 上传到 Release |
| cleanup | 删除临时 sidecar artifact |

### 版本管理

- 版本号在 `src-tauri/tauri.conf.json` 的 `version` 字段（当前 `0.1.4`）
- CI 发布时自动从 git tag 提取版本号更新 `tauri.conf.json` 和 `Cargo.toml`
- 本地构建前如需改版本，手动编辑 `src-tauri/tauri.conf.json`

### 关键配置文件

| 文件 | 用途 |
|------|------|
| `src-tauri/tauri.conf.json` | Tauri 主配置（版本/bundle/externalBin/resources/updater） |
| `src-tauri/src/main.rs` | Rust 主程序（sidecar 生命周期管理/端口注入/窗口创建） |
| `src-tauri/capabilities/default.json` | 权限声明（shell/fs/http 等） |
| `pyinstaller/provisioning-station.spec` | PyInstaller 打包规格 |
| `scripts/build-sidecar.py` | Sidecar 构建脚本（支持 `--target` 交叉编译） |
| `scripts/build-desktop.sh` | 一键构建脚本（`--dev` / `--build` / `--skip-sidecar`） |

---

## 回归测试（每次修改后必须执行）

**原则**：任何代码修改后，必须运行对应层级的测试确保无衰退。不要跳过测试直接提交。

### 测试分层

| 层级 | 命令 | 需要后端？ | 说明 |
|------|------|-----------|------|
| 后端单元测试 | `uv run --group test pytest tests/unit/ -v` | 否 | 模型、解析器、deployer 注册、步骤生成 |
| 前端单元测试 | `cd frontend && npm test` | 否 | API 模块、i18n、参数处理 |
| 后端集成测试 | `uv run --group test pytest tests/integration/ -v` | 是 | API 端点、方案加载、双语加载 |
| API 契约测试 | `uv run --group test pytest tests/integration/test_*_contract.py tests/integration/test_port_configuration.py -v` | 是 | 前后端数据结构一致性 |
| E2E 测试 | `uv run --group test pytest tests/e2e/ -v` | 是 + 真实设备 | 实际设备部署验证 |
| Lint | `uv run ruff check provisioning_station/` | 否 | 代码风格检查 |

### 修改 → 测试映射

| 修改了什么 | 至少运行 |
|-----------|---------|
| `provisioning_station/models/` | 后端单元测试（test_models, test_actions） |
| `provisioning_station/deployers/` | 后端单元测试（test_deployer_registry, test_step_registry） |
| `provisioning_station/services/markdown_parser.py` | 后端单元测试（test_markdown_parser） |
| `provisioning_station/services/solution_manager.py` | 后端单元测试 + 集成测试（test_solution_manager, test_bilingual_loading） |
| `provisioning_station/routers/` | 集成测试（test_api_solutions 等） |
| `frontend/src/modules/api.js` | 前端测试 + 契约测试 |
| `frontend/src/pages/deploy/` | 前端测试（test_params） |
| `shared/constants.py` | 契约测试（test_port_configuration） |
| `solutions/` 目录 | 后端单元测试（test_solution_format）— 验证 guide.md 格式 |
| `solutions/` 目录（方案录入验证） | 按需验证（`pytest tests/unit/test_solution_config_validation.py -v`） |
| 任何不确定的修改 | **全量**：后端单元 + 前端 + 集成测试 |

### 快速全量回归（推荐）

```bash
# 不需要后端运行的测试（快速，30秒内）
uv run --group test pytest tests/unit/ -v && cd frontend && npm test && cd ..

# 需要后端运行的完整回归（先启动 ./dev.sh）
uv run --group test pytest tests/ --ignore=tests/e2e -v
```

### CI 说明

CI (`.github/workflows/test.yml`) 在 PR 和 push 时自动运行：
1. **backend-test**：单元 + 集成（排除需要后端运行的契约测试和 e2e）
2. **frontend-test**：Vitest
3. **contract-test**：启动后端后运行契约测试（依赖 backend-test 通过）
4. **lint**：ruff + black

### 关键测试文件说明

| 测试文件 | 防止什么衰退 |
|---------|-------------|
| `test_deployer_registry.py` | 新增/删除 deployer 后注册表完整性 |
| `test_step_registry.py` | deployer 的 steps 声明与实际生成的步骤一致 |
| `test_markdown_parser.py` | guide.md 的 Step/Target/Preset 解析正确性 |
| `test_solution_format.py` | **所有方案** guide.md 格式规范（扫描真实文件） |
| `test_models.py` | Pydantic 模型序列化/反序列化 |
| `test_deployment_api_contract.py` | 前端期望的 API 响应结构不变 |
| `test_port_configuration.py` | 前后端端口配置一致 |
| `test_bilingual_loading.py` | 中英文 guide.md 结构匹配 |
| `test_deployment_params.py` | 部署参数传递正确 |
| `test_solution_config_validation.py` | 方案设备配置合法性（按需，非 CI） |

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/solutions?lang=zh` | GET | 方案列表 |
| `/api/solutions/{id}?lang=zh` | GET | 方案详情 |
| `/api/solutions/{id}/deployment?lang=zh` | GET | 部署信息（含解析后的步骤） |
| `/api/solutions/{id}/assets/{path}` | GET | 静态资源 |
| `/api/devices/detect/{solution_id}` | GET | USB/串口设备检测 |
| `/api/devices/scan-mdns` | GET | mDNS 局域网设备扫描 |
| `/api/docker-devices/local/check` | GET | 本地 Docker 状态 |
| `/api/docker-devices/local/managed-apps` | GET | 已部署应用列表 |
| `/api/deployments/start` | POST | 启动部署 |
| `/api/deployments/{id}/cancel` | POST | 取消部署 |
| `/ws/deployments/{deployment_id}` | WS | 部署日志 WebSocket |
| `/api/serial-camera/{port}/ws` | WS | 串口摄像头 WebSocket |
| `/api/preview/stream/{stream_id}` | WS | 视频流代理 |

---

## 国际化

- 文件命名：`file.md` / `file_zh.md`
- YAML 字段：`name` / `name_zh`, `summary` / `summary_zh`
- 前端翻译：`frontend/src/modules/i18n.js`

---

## 设计规范

- Primary: `#8CC63F` (Seeed 绿)
- 按钮：`.btn-primary` / `.btn-secondary` / `.btn-deploy-hero`
- 间距：Tailwind 类（`mb-4`, `mt-6`, `gap-3`）
- 样式文件：`frontend/design-system/components.css`
