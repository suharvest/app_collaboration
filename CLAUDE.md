# SenseCraft Solution 开发指南

## 项目概述

SenseCraft Solution 是一个 IoT 解决方案部署平台，用于展示和部署 Seeed Studio 的硬件产品方案。

## 技术栈

- **前端**: Vite + Vanilla JS + Tailwind CSS
- **后端**: Python FastAPI
- **数据格式**: YAML 配置 + Markdown 内容

## 项目结构

```
app_collaboration/
├── frontend/                    # 前端应用
│   ├── src/
│   │   ├── modules/            # 核心模块
│   │   │   ├── api.js          # API 调用
│   │   │   ├── i18n.js         # 国际化
│   │   │   ├── router.js       # 路由
│   │   │   └── __tests__/      # 前端单元测试 (Vitest)
│   │   └── pages/              # 页面组件
│   │       ├── solutions.js    # 方案列表
│   │       ├── solution-detail.js  # 方案详情
│   │       └── deploy/         # 部署页面模块
│   └── design-system/          # 设计系统
│       └── components.css      # 组件样式
├── provisioning_station/       # 后端服务
│   ├── routers/
│   │   └── solutions.py        # 方案 API
│   ├── services/
│   │   └── solution_manager.py # 方案管理
│   └── models/
│       ├── api.py              # API 请求/响应模型
│       └── websocket.py        # WebSocket 消息模型
├── shared/                      # 前后端共享常量
│   └── constants.py            # 端口、语言等配置
├── tests/                       # 后端测试
│   ├── unit/                   # 单元测试
│   └── integration/            # 集成测试 & API 契约测试
└── solutions/                  # 方案配置目录
    └── [solution_id]/          # 单个方案（简化结构）
        ├── solution.yaml       # 方案配置
        ├── description.md      # 英文介绍
        ├── description_zh.md   # 中文介绍
        ├── guide.md            # 英文部署指南
        ├── guide_zh.md         # 中文部署指南
        ├── gallery/            # 图片资源
        └── deploy/sections/    # 部署步骤详情（可选）
```

---

## 文案编写规范（必须遵守）

**重要**：创建或修改 `solutions/` 目录下的任何文档前，**必须先读取** `.claude/skills/solution-copywriting/SKILL.md` 获取完整规范。

规范包括：
- 介绍页四段式结构（痛点、价值、场景、须知）
- 部署页 section 布局规则（description vs troubleshoot 文件分工）
- 术语通俗化对照表
- 质量检查清单

---

## 从 Wiki 文档创建新方案

### 方案 ID 命名规则

- 只能使用小写字母、数字和下划线
- 必须以小写字母开头
- 正则表达式：`^[a-z][a-z0-9_]*$`
- 示例：`my_solution_name`、`smart_factory_v2`、`voice_assistant`

### 步骤 1: 创建方案目录结构

```bash
solutions/
└── your_solution_id/
    ├── solution.yaml       # 方案配置（必须）
    ├── description.md      # 英文介绍（必须）
    ├── description_zh.md   # 中文介绍（必须）
    ├── guide.md            # 英文部署指南（必须）
    ├── guide_zh.md         # 中文部署指南（必须）
    ├── gallery/            # 图片资源
    │   ├── cover.png       # 封面图
    │   └── ...
    └── deploy/sections/    # 部署步骤详情（可选）
        ├── step1.md
        ├── step1_zh.md
        └── ...
```

### 步骤 2: 编写 solution.yaml

```yaml
version: "1.0"
id: your_solution_id
name: Solution Name (English)
name_zh: 方案名称（中文）

intro:
  # 简短摘要（显示在卡片和标题下方）
  summary: One-line description of the solution
  summary_zh: 一句话描述方案

  # Markdown 详细介绍文件（简化路径，直接在根目录）
  description_file: description.md
  description_file_zh: description_zh.md

  # 封面图片
  cover_image: gallery/cover.png

  # 图库（可选）
  gallery:
    - type: image
      src: gallery/demo1.png
      caption: Demo screenshot
      caption_zh: 演示截图

  # 分类和标签
  category: voice_ai  # 或 sensing, automation 等
  tags:
    - iot
    - watcher

  # 设备目录（新格式：定义可复用的设备）
  device_catalog:
    device_key:
      name: Device Name
      name_zh: 设备名称
      image: gallery/device.png
      product_url: https://www.seeedstudio.com/...
      description: Device description
      description_zh: 设备描述

  # 部署预设（多种部署方案）
  presets:
    - id: preset_id
      name: Preset Name
      name_zh: 预设名称
      badge: Recommended       # 可选徽章
      badge_zh: 推荐
      description: Preset description
      description_zh: 预设描述
      device_groups:           # 该预设所需的设备组
        - id: group_id
          name: Group Name
          name_zh: 组名称
          type: single         # single | multiple
          required: true
          options:
            - device_ref: device_key  # 引用 device_catalog 中的设备
          default: device_key
      architecture_image: gallery/architecture.png
      devices:                 # 部署步骤
        - id: step1
          name: Step Name
          name_zh: 步骤名称
          type: docker_deploy  # docker_deploy | docker_local | esp32_usb | script | manual
          required: true
          targets:             # 部署目标（本地/远程）
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/config.yaml
              section:
                description_file: deploy/sections/step1_local.md
                description_file_zh: deploy/sections/step1_local_zh.md
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/config_remote.yaml
              section:
                description_file: deploy/sections/step1_remote.md
                description_file_zh: deploy/sections/step1_remote_zh.md

  # 统计信息
  stats:
    difficulty: beginner  # beginner | intermediate | advanced
    estimated_time: 30min

  # 外部链接
  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

deployment:
  # 部署指南（简化路径，直接在根目录）
  guide_file: guide.md
  guide_file_zh: guide_zh.md
```

### 步骤 3: 编写 Markdown 内容

#### 介绍页 Markdown 规范

**文件**: `description.md` / `description_zh.md`（直接在方案根目录）

```markdown
## 核心价值

- **特点1** - 详细说明
- **特点2** - 详细说明

## 使用场景

| 场景 | 说明 |
|------|------|
| 场景1 | 描述 |
| 场景2 | 描述 |
```

**注意事项**:
- 不要写 H1 标题（页面已有标题）
- 从 H2 (##) 开始
- 表格会自动应用深色边框样式
- 支持标准 Markdown 语法

#### 部署页 Markdown 规范

**文件**: `guide.md` / `guide_zh.md`（直接在方案根目录）

```markdown
## 部署前准备

确保您已准备好以下环境：
- Docker 已安装
- 网络连接正常

## 部署完成后

访问 http://localhost:xxxx 查看结果
```

**注意事项**:
- 一键部署后，不需要写详细的命令步骤
- 只保留用户需要手动操作的内容
- 部署后的验证步骤放在最后

---

## 国际化 (i18n) 规范

### 文件命名

- 英文版: `filename.md`
- 中文版: `filename_zh.md`

### YAML 字段

- 英文字段: `name`, `summary`, `description`
- 中文字段: `name_zh`, `summary_zh`, `description_zh`

### 前端翻译

编辑 `frontend/src/modules/i18n.js`:

```javascript
const translations = {
  en: {
    // 英文翻译
  },
  zh: {
    // 中文翻译
  }
};
```

---

## 常见修改任务

### 修改应用标题

1. 编辑 `frontend/src/modules/i18n.js`:
   ```javascript
   en: { app: { title: 'English Title' } },
   zh: { app: { title: '中文标题' } }
   ```

2. 编辑 `frontend/index.html`:
   ```html
   <title>English Title</title>
   ```

3. 删除 `frontend/dist` 目录（如果存在）

### 修改方案名称

编辑 `solutions/[id]/solution.yaml`:
```yaml
name: New Name
name_zh: 新名称
```

### 调整侧边栏宽度

编辑 `frontend/design-system/components.css`:
```css
.sidebar {
  width: 260px;  /* 调整此值 */
}
```

### 添加新的翻译文本

1. 在 `i18n.js` 中添加 key
2. 在组件中使用 `t('key.path')` 或 `${t('key.path')}`

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/solutions?lang=zh` | GET | 获取方案列表 |
| `/api/solutions/{id}?lang=zh` | GET | 获取方案详情 |
| `/api/solutions/{id}/deployment?lang=zh` | GET | 获取部署信息 |
| `/api/solutions/{id}/assets/{path}` | GET | 获取静态资源 |
| `/api/devices/detect/{solution_id}` | GET | 检测设备 |
| `/api/devices/scan-mdns` | GET | mDNS 局域网设备扫描 |
| `/api/docker-devices/local/check` | GET | 检查本地 Docker 状态 |
| `/api/docker-devices/local/managed-apps` | GET | 获取已部署应用列表 |
| `/api/deployments/start` | POST | 启动部署 |
| `/ws/deployments/{deployment_id}` | WS | 部署日志 WebSocket |

**注意**: `lang` 参数控制返回内容的语言 (`en` 或 `zh`)

### 设备类型

| 类型 | 说明 |
|------|------|
| `docker_local` | 本地 Docker 部署 |
| `docker_deploy` | Docker 部署（支持本地/远程目标） |
| `docker_remote` | 远程 Docker 部署（SSH） |
| `esp32_usb` | ESP32 USB 烧录 |
| `himax_usb` | Himax USB 烧录 |
| `recamera_cpp` | reCamera C++ 部署 |
| `recamera_nodered` | reCamera Node-RED 部署 |
| `ssh_deb` | SSH + DEB 包安装 |
| `script` | 脚本执行 |
| `manual` | 手动步骤 |
| `preview` | 预览步骤（无实际部署） |

### WebSocket 消息类型

部署过程通过 WebSocket 发送实时消息，定义在 `provisioning_station/models/websocket.py`：

| 类型 | 说明 |
|------|------|
| `log` | 日志消息 |
| `status` | 状态更新 |
| `progress` | 进度更新 |
| `device_started` | 设备部署开始 |
| `device_completed` | 设备部署完成 |
| `deployment_completed` | 整体部署完成 |
| `docker_not_installed` | Docker 未安装提示 |

---

## 开发命令

```bash
# 启动开发服务器
./dev.sh

# 前端: http://localhost:5173
# 后端: http://localhost:3260

# 如果页面显示旧内容，删除 dist 并重启
rm -rf frontend/dist
./dev.sh
```

---

## 测试

### 后端测试 (pytest)

**重要**：必须使用 `--group test` 参数，因为 pytest 在 test 依赖组中，不在主依赖中。

```bash
# 运行所有后端测试（单元测试 + 集成测试）
uv run --group test pytest tests/ -v

# 只运行单元测试（不需要后端服务）
uv run --group test pytest tests/unit/ -v

# 只运行集成测试（需要后端服务运行）
uv run --group test pytest tests/integration/ -v

# 运行带覆盖率
uv run --group test pytest tests/ --cov=provisioning_station -v
```

**注意**：
- 单元测试 (`tests/unit/`) 不需要后端服务运行
- 集成测试 (`tests/integration/`) 需要先启动后端服务 (`./dev.sh`)
- 如果直接使用 `uv run pytest` 会报错 `No module named pytest`

### 前端测试 (Vitest)

```bash
cd frontend

# 运行测试
npm test

# 监视模式
npm run test:watch

# 带覆盖率
npm run test:coverage
```

### API 契约测试

契约测试验证前后端数据结构一致性，需要后端服务运行：

```bash
# 1. 先启动后端服务
./dev.sh &
sleep 5

# 2. 运行契约测试
uv run --group test pytest tests/integration/test_*_contract.py -v
```

### 共享常量

`shared/constants.py` 是前后端配置的唯一真实来源：

| 常量 | 值 | 说明 |
|------|-----|------|
| `DEFAULT_PORT` | 3260 | 后端默认端口 |
| `SUPPORTED_LANGUAGES` | ["en", "zh"] | 支持的语言 |
| `REQUEST_TIMEOUT_MS` | 30000 | 请求超时（毫秒） |

修改这些值时需同步更新：
- `frontend/src/modules/api.js`
- `provisioning_station/config.py`

---

## Tauri 桌面应用打包

### 目录结构

```
app_collaboration/
├── src-tauri/                    # Tauri Rust 项目
│   ├── Cargo.toml
│   ├── tauri.conf.json           # Tauri 配置
│   ├── capabilities/default.json # 权限配置
│   ├── binaries/                 # Sidecar 二进制文件
│   ├── icons/                    # 应用图标
│   └── src/main.rs               # Rust 主程序
├── pyinstaller/                  # PyInstaller 配置
│   └── provisioning-station.spec
└── scripts/
    └── build-sidecar.py          # Sidecar 构建脚本
```

### 本地构建步骤

**1. 构建 Python Sidecar**
```bash
cd /Users/harvest/project/app_collaboration
uv run --group build python scripts/build-sidecar.py
```
输出位置: `src-tauri/binaries/provisioning-station-aarch64-apple-darwin`

**2. 构建 Tauri 应用**
```bash
cd /Users/harvest/project/app_collaboration/src-tauri  # 重要：必须在 src-tauri 目录下运行
cargo tauri build
```
- `beforeBuildCommand` 会自动构建前端 (`npm run build --prefix frontend`)
- 输出位置: `src-tauri/target/release/bundle/macos/SenseCraft Solution.app`
- DMG 位置: `src-tauri/target/release/bundle/dmg/SenseCraft Solution_1.0.0_aarch64.dmg`

### 开发模式
```bash
cd /Users/harvest/project/app_collaboration/src-tauri
cargo tauri dev
```

### 架构说明

- **Sidecar 模式**: Python 后端通过 PyInstaller 打包为独立可执行文件
- **动态端口**: Tauri 使用 portpicker 选择可用端口，避免端口冲突
- **Solutions 资源**: 通过 Tauri resources 打包到 `Contents/Resources/_up_/solutions/`
- **端口通信**: Rust 通过 `window.eval()` 注入 `window.__BACKEND_PORT__` 到前端

---

## 设计规范

### 颜色变量

- `primary`: #8CC63F (Seeed 绿)
- `text-primary`: #1a1a1a
- `text-secondary`: #666
- `border`: #e5e5e5

### 按钮样式

- `.btn-primary`: 主要操作按钮
- `.btn-secondary`: 次要操作按钮
- `.btn-deploy-hero`: 大号部署按钮

### 间距

使用 Tailwind 类: `mb-4`, `mt-6`, `gap-3` 等
