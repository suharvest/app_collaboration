---
name: solution-validation
description: 验证 IoT 解决方案并生成部署指南。基于原始资料复现方案，提炼最简路径，录制 Demo 视频，输出符合规范的 guide.md / description.md。适用于：从 Wiki/文档创建新方案、验证已有方案可复现性、录制方案演示视频。
argument-hint: "<资料来源URL或路径> [solution_id]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch, Task
---

# Solution Validation Skill

## 调用方式

```
/solution-validation https://wiki.seeedstudio.com/xxx smart_factory
/solution-validation ./raw_materials/ my_solution
/solution-validation https://github.com/xxx/xxx  # 自动生成 solution_id
```

## 参数说明

- `$ARGUMENTS` 包含：资料来源（URL 或本地路径）+ 可选的 solution_id

---

## 核心理念

**目标用户**：解决方案商（无开发能力）
**最小工作单元**：**preset**（而非整个 solution）。如果用户明确指定了某个 preset，只复现和准备该 preset，不检查同方案下的其他 preset。
**核心原则**：

1. **最简路径**：去掉所有非必要步骤，让用户用最少操作完成部署
2. **预配置优先**：能提前配好的全部预配好，用户只需做「连接」和「点击」
3. **关键配置暴露**：保留方案拓展性，将常用配置项（如 WiFi、服务器地址）作为可修改参数
4. **录屏验证**：每个关键步骤录制 Demo，确保可复现

---

## 执行流程

### Phase 1: 资料收集与分析

**Step 1**: 读取/抓取原始资料
- 如果是 URL：使用 WebFetch 或 firecrawl 抓取内容
- 如果是本地路径：读取所有相关文件
- 如果是 Git 仓库：clone 并分析 README、docs、docker-compose 等

**Step 2**: 分析资料，提取关键信息

生成结构化摘要：

```
## 方案概述
- 名称：
- 解决什么问题：
- 核心硬件：
- 核心软件：

## 部署步骤（原始）
1. ...
2. ...

## 识别出的问题
- [ ] 步骤 X 对非技术用户太复杂
- [ ] 步骤 Y 可以预配置
- [ ] 缺少 Z 的说明

## 简化方案
- 合并/删除的步骤：
- 预配置的内容：
- 暴露的配置项：
```

**Step 3**: 向用户确认简化方案，获得批准后继续

---

### Phase 2: 环境准备与复现

**Step 4**: 加载设备配置 & 准备验证环境

首先读取 `.claude/devices.yaml` 获取设备凭证：
```bash
# 读取设备配置文件
Read .claude/devices.yaml
```

该文件结构：
```yaml
recamera:
  host: "192.168.42.1"
  username: "root"
  password: "recamera"
recomputer:
  host: "192.168.10.79"
  username: "harvest"
  password: "12345678"
jetson:
  host: "192.168.1.100"
  username: "nvidia"
  ssh_key: "~/.ssh/id_rsa"
watcher:
  serial_port: ""  # 留空 = 自动检测
local_docker:
  note: "本机 Docker，无需凭证"
```

> **文件位置**：`.claude/devices.yaml`（已加入 .gitignore，不会提交）
> **修改方式**：用户随时直接编辑此文件更新 IP/密码等

然后：
- 根据方案所需设备类型，从配置中提取对应凭证
- 检查所需工具是否已安装（Docker、串口工具等）
- 准备硬件连接（如有）
- 创建工作目录

**Step 5**: 按简化后的步骤逐步执行
- 每个步骤执行前，用 `playwright-cli` 启动录屏（如涉及 Web 界面）
- 记录每步的实际命令、输出、耗时
- 遇到问题立即记录到故障排查表

录屏工作流：
```bash
# 涉及 Web 界面的步骤
playwright-cli open http://localhost:8080
playwright-cli video-start
# ... 执行操作（每个操作间留 1-2 秒间隔）...
playwright-cli video-stop solutions/<id>/gallery/step1-demo.webm

# 将 webm 转换为 GIF（640px 宽，1.5x 倍速，用于文档嵌入）
ffmpeg -i solutions/<id>/gallery/step1-demo.webm \
  -vf "setpts=PTS/1.5,fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  solutions/<id>/gallery/step1-demo.gif

# 截图关键画面
playwright-cli screenshot --filename=solutions/<id>/gallery/step1-result.png
```

GIF 转换参数说明：
- `fps=10`：10 帧/秒，平衡清晰度和文件大小
- `scale=640:-1`：宽度 640px，高度等比缩放
- `lanczos`：高质量缩放算法
- `palettegen + paletteuse`：两遍编码，GIF 色彩最优

> **什么时候录 GIF**：涉及 Web 界面的交互操作（点击按钮、配置表单、查看仪表盘等）都应录制 GIF。纯命令行或自动化部署步骤不需要。

**Step 6**: 验证最终结果
- 确认所有功能正常
- 截图/录屏最终效果

---

### Phase 3: 输出文档

**Step 7**: 生成 solution 目录结构

```
solutions/<solution_id>/
├── solution.yaml           # 方案配置
├── description.md          # 英文介绍
├── description_zh.md       # 中文介绍
├── guide.md                # 英文部署指南
├── guide_zh.md             # 中文部署指南
├── gallery/                # 截图和录屏
│   ├── cover.png
│   ├── architecture.png
│   ├── step1-demo.webm     # 步骤演示视频
│   ├── step1-result.png    # 步骤结果截图
│   └── ...
└── devices/                # 设备配置（如需要）
    └── docker.yaml
```

**Step 8**: 按规范编写各文件

> **必须遵循** `.claude/skills/solution-copywriting/SKILL.md` 中的全部规范。
> 以下为关键要点提醒，完整规范请直接参考该文件。

#### description.md / description_zh.md

必须包含四段式结构：
1. `## 这个方案能帮你做什么` — 1-2 句通俗描述
2. `## 核心价值` — 表格，3-4 个要点
3. `## 适用场景` — 表格，具体使用示例
4. `## 使用须知` — 设备要求 + 网络要求 + 可选对比

#### guide.md / guide_zh.md

遵循部署页文案标准：
- Preset 头：`## Preset: Name {#id}` / `## 套餐: 名称 {#id}`
- Step 头：`## Step N: Title {#id type=xxx required=true}` / `## 步骤 N: 标题 {#id type=xxx required=true}`
- 每个 Step 标题下方建议写一句描述文字（会自动作为卡片副标题显示）
- 每个 Step 必须有 `### Wiring` / `### 接线`（如涉及硬件）
- 每个 Step 必须有 `### Troubleshooting` / `### 故障排查`（表格格式）
- 有部署后操作的 Step 应有 `### Deployment Complete` / `### 部署完成`（绿色背景提示区）
- 末尾必须有 `# Deployment Complete` / `# 部署完成`

**Step 9**: 运行质量检查

使用 solution-copywriting SKILL.md 中的「五、质量检查清单」逐项检查。

---

## 简化决策框架

### 什么该预配置（用户不需要碰）

| 类别 | 示例 | 处理方式 |
|------|------|----------|
| 开发依赖 | Python 环境、Node.js 版本 | Docker 打包，用户不感知 |
| 编译步骤 | 固件编译、前端构建 | 提供预编译产物 |
| 系统配置 | 内核参数、驱动安装 | 写入部署脚本自动执行 |
| 默认参数 | 数据库密码、内部端口 | 硬编码合理默认值 |

### 什么该暴露（用户可能需要改）

| 类别 | 示例 | 暴露方式 |
|------|------|----------|
| 网络配置 | WiFi SSID/密码、服务器 IP | 部署界面输入框或环境变量 |
| 设备地址 | 串口号、设备 IP | 自动检测 + 手动输入 |
| 部署后可变参数 | 外部服务 IP、API 端点 | device YAML `reconfigurable: true` + compose `${VAR}` |
| 业务参数 | 检测阈值、通知邮箱 | Web 管理界面 |
| 云服务凭证 | API Key、Account ID | 部署步骤中引导用户获取 |

### 什么该删掉（原始资料中不需要的）

| 类别 | 示例 | 理由 |
|------|------|------|
| 开发调试 | 日志级别调整、Debug 模式 | 用户不需要 |
| 替代方案 | "你也可以用 X 代替 Y" | 增加决策负担 |
| 原理解释 | 算法原理、架构设计 | 用户只关心怎么用 |
| 版本历史 | Changelog、迁移指南 | 与首次部署无关 |

### 手动步骤自动化模式

原始文档中标记为 `type=manual` 的步骤，应逐一审查是否能自动化。核心思路：**如果一个"手动"步骤的本质是在某个设备上执行命令，那它就能变成 action**。

#### 审查流程

```
manual 步骤 → 本质是什么？
│
├─ 在部署目标设备上执行命令
│   ├─ 命令在部署前执行 → actions.before
│   └─ 命令在部署后执行 → actions.after
│
├─ 在用户电脑上执行命令（配置外设等）
│   └─ 能否改为在目标设备上执行？→ 见下方"外设配置转移"
│
├─ 用户需要物理操作（接线、插卡、按按钮）
│   └─ 保留 manual，无法自动化
│
└─ 用户需要访问外部平台（注册账号、获取 API Key）
    └─ 保留 manual，无法自动化
```

#### 外设配置转移模式

当原始步骤要求用户在电脑上配置外设（如 USB 设备），应优先考虑把配置转移到部署目标设备上执行：

**问题**：reSpeaker 配置要求用户先连电脑、装工具、跑命令，再拔线换到 reRouter
**分析**：
1. reSpeaker 最终要连 reRouter → 直接插 reRouter 更自然
2. 配置工具 `xvf_host` 只有 glibc 二进制 → OpenWrt (musl) 跑不了
3. 但 Docker 容器内有 glibc 环境 + Python + pyusb → 可以跑
4. 容器镜像在 Step 3 (docker_deploy) pull 完后就可用
5. `docker run --rm --privileged` 一次性运行，零残留

**解法**：在 `actions.after` 中用已拉取的容器执行配置

```yaml
actions:
  after:
    - name: Configure USB peripheral
      name_zh: 配置 USB 外设
      run: |
        docker run --rm --privileged \
          -v /dev/bus/usb:/dev/bus/usb \
          already-pulled-image:tag \
          python3 -c "...usb config script..."
      ignore_error: true  # 外设未连接时不阻塞
```

**关键约束**：
- 容器镜像必须是同一步骤已经 pull 的（不能依赖外部网络额外下载）
- `--rm` 确保零残留，不留多余容器
- `--privileged` + `-v /dev/bus/usb` 获取 USB 访问权限
- `ignore_error: true` 防止外设未接入时阻塞整个部署
- 配置脚本应内联在 YAML 中（不依赖外部文件）

#### 决策原则

| 原则 | 说明 |
|------|------|
| **方案专属，不改通用组件** | 自动化逻辑放在方案的 device YAML `actions` 中，不修改通用 deployer |
| **利用已有资源** | 优先复用已拉取的镜像、已安装的工具，不引入额外依赖 |
| **环境适配** | 目标设备 libc 不兼容时（如 OpenWrt musl vs glibc），用容器桥接 |
| **优雅降级** | `ignore_error: true` 让非关键配置失败不阻塞主流程 |
| **物理操作不可消除** | 接线、插拔等物理动作无法自动化，但可以减少次数（如从"连电脑配置→拔→连设备"简化为"直接连设备"） |

---

## 录屏规范

### 命名规则

```
solutions/<id>/gallery/
├── step<N>-<action>.webm       # 步骤演示视频（原始录制）
├── step<N>-<action>.gif        # 步骤演示 GIF（640px，文档嵌入用）
├── step<N>-<action>.png        # 关键截图
├── result-<feature>.webm       # 最终效果演示
├── result-<feature>.gif        # 最终效果 GIF
└── result-<feature>.png        # 最终效果截图
```

### 录制要点

1. **开头**：先展示当前页面全貌（snapshot），让观看者知道起点
2. **操作**：每个操作之间留 1-2 秒间隔，便于观看
3. **结果**：操作后等待结果加载完成再停止录制
4. **时长**：单个视频控制在 30 秒以内，复杂流程拆分多段
5. **窗口大小**：录制前用 `playwright-cli resize 1280 800` 设定统一尺寸

### GIF 导出规范

所有涉及 Web 界面操作的步骤，**必须同时导出 GIF**，用于文档嵌入和快速预览。

**转换命令**：
```bash
# 标准 GIF（640px 宽，10fps，1.5x 倍速）
ffmpeg -i input.webm \
  -vf "setpts=PTS/1.5,fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  output.gif

# 2x 倍速（操作简单但耗时的步骤，如等待加载）
ffmpeg -i input.webm \
  -vf "setpts=PTS/2,fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  output.gif

# 如果 GIF 超过 5MB，可组合降帧率 + 加速 + 裁剪
ffmpeg -i input.webm \
  -vf "setpts=PTS/2,fps=8,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -t 15 output.gif
```

**倍速选择**：

| 场景 | 倍速 | setpts 值 | 说明 |
|------|------|-----------|------|
| 需要看清每步操作 | 1.5x | `PTS/1.5` | **默认推荐**，信息密度高且不影响理解 |
| 简单重复操作 | 2x | `PTS/2` | 如连续填表、批量配置 |
| 等待加载/启动过程 | 3x | `PTS/3` | 只需看到结果，过程不重要 |
| 关键复杂操作 | 1x | 不加 setpts | 需要仔细观看的操作不加速 |

**GIF 质量标准**：

| 参数 | 标准值 | 说明 |
|------|--------|------|
| 宽度 | 640px | 高度等比缩放 |
| 帧率 | 10fps | 兼顾流畅和文件大小 |
| 时长 | ≤30s | 单个 GIF 不超过 30 秒 |
| 文件大小 | ≤5MB | 超过则降帧率或拆分 |

**哪些操作需要录 GIF**：

| 场景 | 是否录 GIF | 说明 |
|------|-----------|------|
| Web 界面首次打开 | 是 | 展示加载过程和初始状态 |
| 表单填写与提交 | 是 | 展示用户需要填什么、点哪里 |
| 仪表盘/数据可视化 | 是 | 展示实时数据刷新效果 |
| 配置页面操作 | 是 | 展示具体配置路径和选项 |
| Node-RED 流编辑 | 是 | 展示节点连接和部署过程 |
| 纯命令行自动部署 | 否 | 截图即可 |
| 设备连线/硬件操作 | 否 | 用照片或示意图 |

**guide.md 中嵌入 GIF**：
```markdown
## Step 3: Configure Dashboard {#dashboard type=manual required=true}

Open Grafana at `http://<host>:3000` and import the dashboard:

![Configure Grafana Dashboard](gallery/step3-grafana-config.gif)

### Troubleshooting
...
```

### 截图要点

1. 截取关键结果画面（成功提示、数据展示等）
2. 用于 guide.md 中的步骤说明配图
3. 格式优先 PNG（清晰），照片类可用 JPG

### 完整录制流程示例

以"配置 Grafana 仪表盘"为例：

```bash
# 1. 设置窗口尺寸
playwright-cli resize 1280 800

# 2. 打开目标页面
playwright-cli open http://localhost:3000

# 3. 开始录制
playwright-cli video-start

# 4. 等待页面加载完成（给观看者看到起点）
playwright-cli snapshot
# （等 2 秒）

# 5. 执行操作序列
playwright-cli click e5          # 点击 Dashboards
# （等 1 秒）
playwright-cli click e12         # 点击 Import
# （等 1 秒）
playwright-cli fill e8 "12345"   # 输入 Dashboard ID
playwright-cli click e15         # 点击 Load
# （等 2 秒，等结果加载完）

# 6. 截图最终结果
playwright-cli screenshot --filename=solutions/<id>/gallery/step3-grafana-result.png

# 7. 停止录制
playwright-cli video-stop solutions/<id>/gallery/step3-grafana-config.webm

# 8. 转换为 GIF（1.5x 倍速，提高信息密度）
ffmpeg -i solutions/<id>/gallery/step3-grafana-config.webm \
  -vf "setpts=PTS/1.5,fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  solutions/<id>/gallery/step3-grafana-config.gif

# 9. 检查 GIF 大小
ls -lh solutions/<id>/gallery/step3-grafana-config.gif
# 如果 >5MB，用降帧率版本重新转换
```

---

## 部署类型封装参考

根据方案特点选择合适的部署类型。每个类型对应平台的一种自动化部署能力。

### 类型速查表

| 类型 | 适用场景 | 用户操作 | 所需产物 |
|------|----------|----------|----------|
| `docker_deploy` | 服务端应用（Web、API、数据库） | 点击部署 | docker-compose.yml |
| `esp32_usb` | ESP32 固件烧录 | 插线 + 点击 | firmware.bin |
| `himax_usb` | Himax WE2 固件/模型烧录 | 插线 + 点击 | firmware.bin + .tflite |
| `recamera_cpp` | reCamera C++ 应用 | 输入 IP + 点击 | .deb + .cvimodel |
| `recamera_nodered` | reCamera Node-RED 流 | 输入 IP + 点击 | flow.json |
| `ssh_deb` | 远程 Linux 设备 DEB 安装 | 输入 IP/密码 + 点击 | .deb + config |
| `ha_integration` | HA 自定义集成部署 | 输入 HA 地址/密码 + 点击 | custom_components/ 目录 |
| `script` | 本地脚本/服务启动 | 填配置 + 点击 | shell script |
| `manual` | 纯人工操作步骤 | 按说明操作 + 点完成 | 无 |
| `preview` | 视频流/MQTT 预览 | 输入地址 + 查看 | 无 |

### docker_deploy（最常用）

适用于所有容器化的服务端应用。支持本地部署和远程部署两种 Target。

**guide.md 中的写法**：
```markdown
## Step 1: Deploy Services {#backend type=docker_deploy required=true config=devices/docker.yaml}

Deploy the backend services on your device.

### Target: Local Deployment {#backend_local type=local config=devices/docker.yaml default=true}

Deploy on your local computer.

### Wiring

1. Ensure Docker is running
2. Click Deploy

### Deployment Complete

1. Open **http://localhost:8080** in your browser
2. Create your admin account

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Docker not found | Install Docker Desktop |

### Target: Remote Deployment {#backend_remote type=remote config=devices/docker_remote.yaml}

Deploy to a remote device via SSH.

### Wiring

1. Enter device IP and SSH credentials
2. Click Deploy

### Deployment Complete

1. Open **http://\<device-ip\>:8080** in your browser
2. Create your admin account

### Troubleshooting
| Issue | Solution |
|-------|----------|
| SSH failed | Check IP and credentials |
```

> ⚠️ **注意**：Target 标题下只写一行简短描述。表格、列表等详细内容必须放在 `### Wiring` 子节中，否则会以原始 markdown 文本显示在选择卡片上。

**设备配置 `devices/docker.yaml`**：
```yaml
version: "1.0"
id: server
name: Server
type: docker_local

docker:
  compose_file: assets/docker/docker-compose.yml
  environment:
    CUSTOM_VAR: "value"
    DB_HOST: "{{db_host}}"           # Template var, reconfigurable post-deploy
  options:
    project_name: my_project
    remove_orphans: true
  services:
    - name: backend
      port: 8080
      health_check_endpoint: /api/health
      required: true

user_inputs:
  - id: db_host
    name: Database Host
    name_zh: 数据库地址
    type: text
    default: "localhost"
    reconfigurable: true             # Can update from Devices page after deploy
```

**设备配置 `devices/docker_remote.yaml`**：
```yaml
version: "1.0"
id: server_remote
name: Server (Remote)
type: docker_remote

ssh:
  port: 22
  default_user: admin

docker_remote:
  compose_file: assets/docker/docker-compose.yml
  compose_dir: assets/docker
  remote_path: /home/{{username}}/deploy
  options:
    project_name: my_project
  services:
    - name: backend
      port: 8080
      health_check_endpoint: /api/health

user_inputs:
  - id: host
    name: Host / IP
    type: text
    required: true
  - id: username
    name: SSH Username
    type: text
    default: admin
  - id: password
    name: SSH Password
    type: password
    required: true
```

**所需产物**：
```
solutions/<id>/
├── assets/docker/
│   ├── docker-compose.yml    # 编排文件
│   └── .env                  # 可选环境变量
└── devices/
    ├── docker.yaml           # 本地部署配置
    └── docker_remote.yaml    # 远程部署配置
```

**注意**：
- 本地部署仅支持 Linux/macOS，Windows 用户需选远程部署
- docker-compose.yml 中的镜像必须已推送到可访问的 registry
- 平台会自动注入 `com.sensecraft.*` label 用于追踪管理
- 可重配置环境变量：在 compose 文件中用 `${VAR}` 语法，device YAML 中用 `{{template_var}}` + `reconfigurable: true`，部署后可从 Devices 页面修改

### esp32_usb

适用于 ESP32/ESP32-S3/ESP32-C3 固件烧录。

**设备配置示例**：
```yaml
version: "1.0"
id: device_esp32
name: My ESP32 Device
type: esp32_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"

firmware:
  source:
    type: local
    path: assets/firmware/firmware.bin
  flash_config:
    chip: esp32s3
    baud_rate: 921600
    flash_mode: dio
    flash_size: 16MB
    partitions:
      - name: app
        offset: "0x10000"
        file: firmware.bin
```

**所需产物**：预编译的 firmware.bin（用户不应看到编译过程）

### himax_usb

适用于 SenseCAP Watcher (Himax WE2) 固件和 AI 模型烧录。

**设备配置示例**：
```yaml
version: "1.0"
id: watcher_himax
name: SenseCAP Watcher
type: himax_usb

detection:
  method: usb_serial
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"

firmware:
  source:
    type: local
    path: assets/firmware/himax_firmware.bin
  flash_config:
    baudrate: 921600
    protocol: xmodem
    requires_esp32_reset_hold: true
    models:
      - id: face_detection
        name: Face Detection Model
        path: assets/models/face_detect.tflite
        flash_address: "0xB7B000"
        required: false
        default: true
```

**所需产物**：预编译的 firmware.bin + .tflite 模型文件

### recamera_cpp

适用于 reCamera 设备的 C++ 应用部署（SSH + opkg）。

**设备配置示例**：
```yaml
version: "1.0"
id: recamera_app
name: reCamera Application
type: recamera_cpp

ssh:
  port: 22
  default_user: recamera

binary:
  deb_package:
    path: packages/myapp_0.1_riscv64.deb
    name: myapp
    includes_init_script: true
  models:
    - path: packages/model.cvimodel
      target_path: /userdata/local/models
      filename: model.cvimodel
  conflict_services:
    stop: [S03node-red, S91sscma-node]
  auto_start: true

# 用 actions 替代旧的 mqtt_config 和 disable 字段
actions:
  after:
    - name: Enable MQTT external access
      name_zh: 启用 MQTT 外部访问
      sudo: true
      run: |
        CONF="/etc/mosquitto/mosquitto.conf"
        grep -q 'listener 1883 0.0.0.0' "$CONF" 2>/dev/null && exit 0
        echo "listener 1883 0.0.0.0" >> "$CONF"
        echo "allow_anonymous true" >> "$CONF"
        killall mosquitto 2>/dev/null || true
        sleep 1
        /usr/sbin/mosquitto -c "$CONF" -d
    - name: Disable Node-RED autostart
      name_zh: 禁用 Node-RED 自启动
      sudo: true
      run: |
        for svc in node-red sscma-node; do
          for f in /etc/init.d/S*${svc}*; do
            [ -f "$f" ] && mv "$f" "$(echo "$f" | sed 's|/S|/K|')" 2>/dev/null
          done
        done

user_inputs:
  - id: host
    name: Device IP
    type: text
    default: "192.168.42.1"
    required: true
  - id: password
    name: SSH Password
    type: password
    default: "recamera"
    required: true
```

**所需产物**：.deb 包（含 init script）+ .cvimodel 模型
**注意**：`steps` 无需声明，由 step registry 自动生成；`actions_after` 步骤仅在有 `actions.after` 时包含

### recamera_nodered

适用于 reCamera 设备的 Node-RED 流部署。

**设备配置示例**：
```yaml
version: "1.0"
id: recamera_flow
name: reCamera Node-RED Flow
type: recamera_nodered

ssh:
  port: 22
  default_user: recamera

nodered:
  flow_file: assets/flows/default-flow.json
  port: 1880

user_inputs:
  - id: host
    name: Device IP
    type: text
    required: true
  - id: password
    name: SSH Password
    type: password
    required: true
```

**所需产物**：flow.json 流文件

### ha_integration

适用于 Home Assistant 自定义集成部署。自动处理 HA 认证、SSH 配置、文件复制、重启和集成注册。支持 HA OS（自动安装 SSH addon）和 Docker Core。

**设备配置示例**：
```yaml
version: "1.0"
id: homeassistant_integration
name: Home Assistant Integration
type: ha_integration

ha_integration:
  domain: recamera                                    # HA integration domain
  components_dir: assets/docker/custom_components/recamera  # 组件文件目录
  config_flow_data:                                   # config flow 提交的数据
    - name: host
      value_from: device_ip                           # 从 user_inputs 取值
    - name: port
      value_from: device_port
      type: int                                       # 类型转换
    - name: mode
      value: auto                                     # 静态值

user_inputs:
  - id: host
    name: HA Address
    type: text
    required: true
  - id: username
    name: HA Username
    type: text
    required: true
  - id: password
    name: HA Password
    type: password
    required: true
  - id: device_ip
    name: Device IP
    type: text
    required: true
  - id: ssh_username
    name: SSH Username (Docker only)
    type: text
    required: false
  - id: ssh_password
    name: SSH Password (Docker only)
    type: password
    required: false
```

**所需产物**：`custom_components/<domain>/` 目录（含 `__init__.py`、`manifest.json` 等）

**自动步骤序列**：auth → detect → ssh → copy → restart → integrate

### script

适用于本地脚本执行，可配合用户输入进行参数化。

**设备配置示例**：
```yaml
version: "1.0"
id: local_service
name: Local Service
type: script

script:
  working_dir: "app_directory"
  config_template:
    file: "config.yml"
    content: |
      api_key: "{{api_key}}"
      endpoint: "{{server_url}}"
  start_command:
    linux_macos: "./start.sh"
    windows: "start.bat"
  health_check:
    type: log_pattern
    pattern: "Server started"
    timeout_seconds: 30

user_inputs:
  - id: api_key
    name: API Key
    type: password
    required: true
  - id: server_url
    name: Server URL
    type: text
    placeholder: "https://api.example.com"
    required: true
```

**所需产物**：启动脚本 + 配置模板
**变量替换**：`{{variable}}` 会被 user_inputs 的值替换

### manual

纯展示步骤，无自动化部署。用户看完说明后手动点击"完成"。

**guide.md 中直接写步骤内容即可，无需设备配置文件**：
```markdown
## Step 2: Configure Platform {#platform type=manual required=true}

### Wiring

1. Open browser and visit http://localhost:8080
2. Register an admin account
3. Configure your API settings

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Wait 30s for services to start |
```

### preview

用于展示实时视频流和 MQTT 推理数据，一般作为最后的验证步骤。

**设备配置示例**：
```yaml
version: "1.0"
id: live_preview
name: Live Preview
type: preview

video:
  type: rtsp_proxy
  rtsp_url_template: "rtsp://{{host}}:554/stream"

mqtt:
  broker_template: "{{host}}"
  port: 1883
  topic_template: "inference/{{device_id}}"

user_inputs:
  - id: host
    name: Device IP
    type: text
    required: true
```

---

### Actions（钩子系统）

所有部署类型都支持 `actions` 字段，用于在部署前后执行自定义命令。这是把原始方案中零散的手动步骤**自动化**的核心机制。

#### 生命周期

```
[before actions] → 主部署流程（pull/flash/install…）→ [after actions]
```

| 阶段 | 时机 | 典型用途 |
|------|------|----------|
| `before` | 主部署之前 | 创建目录、导入离线镜像、设置权限 |
| `after` | 主部署之后 | 配置 MQTT、禁用冲突服务、写入配置文件 |

#### YAML 语法

```yaml
actions:
  before:
    - name: "Action name"
      name_zh: "操作名称"
      run: |                          # shell 命令（多行）
        mkdir -p /data/models
      copy:                           # 或复制文件（与 run 二选一）
        src: "config/app.conf"        # 相对于 solution 目录
        dest: "/etc/app.conf"
        mode: "0644"
      when:                           # 条件执行（可选）
        field: "user_input_id"        # user_inputs 中的字段 ID
        value: "expected_value"       # 匹配时执行
        # 或 not_value: "skip_value"  # 不匹配时执行
      sudo: true                      # 用 sudo（仅 SSH 类型）
      env:                            # 环境变量（可选）
        VAR: "{{substitution}}"       # 支持变量替换
      timeout: 300                    # 超时秒数（默认 300）
      ignore_error: false             # 失败是否继续（默认 false）
  after:
    - name: "Post action"
      # 同上
```

#### 变量替换

`run`、`env`、`copy` 路径中的 `{{variable}}` 会被替换为 `user_inputs` 字段值和连接参数。

#### Steps 自动生成

**不需要在 YAML 中手动声明 `steps`**。加载设备配置时，系统根据 `type` 从 step registry 自动生成步骤序列：

```
load_device_config() → config.steps 为空？
    → 是：调用 get_steps_for_config(config) 自动生成
    → 否：保留 YAML 中声明的 steps（不覆盖）
```

**自动生成规则**：
- `actions_before` 步骤仅在 `actions.before` 非空时包含
- `actions_after` 步骤仅在 `actions.after` 非空时包含
- `manual` 类型不在注册表中，返回空列表——需要在 YAML 中手动声明 `steps`

**各类型的自动步骤序列**（`*` 标记条件步骤）：

| docker_local | docker_remote | esp32_usb |
|---|---|---|
| *actions_before | connect | detect |
| pull_images | check_os | *actions_before |
| create_volumes | check_docker | erase |
| start_services | prepare | flash |
| health_check | *actions_before | verify |
| *actions_after | upload | *actions_after |
| | pull_images | |
| | start_services | |
| | health_check | |
| | *actions_after | |

| himax_usb | recamera_cpp | ha_integration | script |
|---|---|---|---|
| detect | connect | auth | validate |
| prepare | precheck | detect | *actions_before |
| *actions_before | prepare | ssh | setup |
| flash | transfer | copy | configure |
| verify | install | restart | start |
| *actions_after | models | integrate | health_check |
| | configure | | *actions_after |
| | *actions_after | | |
| | start | | |
| | verify | | |

#### 执行器类型

| 部署类型 | 执行器 | 说明 |
|----------|--------|------|
| docker_local, esp32_usb, himax_usb, script, recamera_nodered | LocalActionExecutor | 本机 shell |
| docker_remote, ssh_deb, recamera_cpp, ha_integration | SSHActionExecutor | 远程 SSH（支持 sudo） |

#### 实战示例

**Docker Remote + 离线/在线条件**：
```yaml
actions:
  before:
    - name: Import Docker image (offline)
      name_zh: 导入 Docker 镜像（离线）
      when:
        field: deploy_method
        value: offline
      run: gunzip -c app.tar.gz | docker import - myapp:v1.0
```

**reCamera C++ after hooks**（替代旧的 mqtt_config + disable）：
```yaml
actions:
  after:
    - name: Enable external MQTT access
      name_zh: 启用 MQTT 外部访问
      sudo: true
      run: |
        CONF="/etc/mosquitto/mosquitto.conf"
        grep -q 'listener 1883 0.0.0.0' "$CONF" 2>/dev/null && exit 0
        echo "listener 1883 0.0.0.0" >> "$CONF"
        echo "allow_anonymous true" >> "$CONF"
        killall mosquitto 2>/dev/null || true
        sleep 1
        /usr/sbin/mosquitto -c "$CONF" -d
    - name: Disable Node-RED autostart
      name_zh: 禁用 Node-RED 自启动
      sudo: true
      run: |
        for svc in node-red sscma-node; do
          for f in /etc/init.d/S*${svc}*; do
            [ -f "$f" ] && mv "$f" "$(echo "$f" | sed 's|/S|/K|')" 2>/dev/null
          done
        done
```

**SSH Remote + ignore_error**：
```yaml
actions:
  before:
    - name: Create data directories
      name_zh: 创建数据目录
      run: mkdir -p /data/recordings /data/models
    - name: Set audio device permissions
      name_zh: 设置音频设备权限
      run: chmod -R 666 /dev/snd/* || true
      ignore_error: true
```

**Docker Remote + USB 外设配置（利用已拉取镜像）**：
```yaml
# 场景：reSpeaker XVF3800 需要关闭回声消除，原方案要求用户在电脑上配置
# 优化：部署时直接在目标设备上用容器跑配置脚本
actions:
  after:
    - name: Configure reSpeaker audio output
      name_zh: 配置 reSpeaker 音频输出
      run: |
        docker run --rm --privileged \
          -v /dev/bus/usb:/dev/bus/usb \
          registry.example.com/voice-client:v1.0 \
          python3 -c "
        import sys, usb.core, usb.util
        dev = usb.core.find(idVendor=0x2886, idProduct=0x001A)
        if not dev:
            print('reSpeaker not found, skipping')
            sys.exit(0)
        dev.ctrl_transfer(0x40, 0, 10, 48, [1], 100000)  # CLEAR_CONFIGURATION
        dev.ctrl_transfer(0x40, 0, 19, 35, [8, 0], 100000)  # AUDIO_MGR_OP_R 8 0
        dev.ctrl_transfer(0x40, 0, 9, 48, [1], 100000)  # SAVE_CONFIGURATION
        print('reSpeaker configured')
        usb.util.dispose_resources(dev)
        "
      ignore_error: true  # reSpeaker 未连接时不阻塞部署
```

> **要点**：镜像 `voice-client:v1.0` 是同步骤 docker compose pull 已拉取的，
> 容器内已有 Python + pyusb + libusb，无需额外安装。
> `--rm` 保证一次性运行无残留。设备未连接时 `sys.exit(0)` + `ignore_error` 双重保底。

#### 封装时的 actions 决策

| 原始操作 | actions 处理 |
|----------|-------------|
| 部署前创建目录/设置权限 | `before` + `run` |
| 部署前导入离线资源 | `before` + `run` + `when` |
| 部署后配置网络/MQTT | `after` + `run` + `sudo` |
| 部署后禁用冲突服务 | `after` + `run` + `sudo` |
| 部署后复制配置文件 | `after` + `copy` |
| 部署后配置 USB 外设 | `after` + `docker run --rm` + `ignore_error` |
| 根据用户选择走不同路径 | `when.field` + `when.value` |
| 可能失败不影响主流程 | `ignore_error: true` |

> **原则**：能用 actions 自动化的，就不要留给用户手动操作。

---

### 封装决策流程图

根据方案的原始部署方式，选择最合适的类型：

```
原始方案用了什么？
│
├─ docker-compose / Docker → docker_deploy
│   ├─ 只在本地跑 → 只配 local target
│   ├─ 要部署到远程设备 → 配 local + remote targets
│   └─ 有多组服务 → 拆成多个 docker_deploy 步骤
│
├─ ESP32 固件 → esp32_usb
│   └─ 预编译好 .bin，用户只需插线点击
│
├─ Himax WE2 / Watcher 固件 → himax_usb
│   └─ 预编译 firmware + tflite 模型
│
├─ reCamera 应用 (C++) → recamera_cpp
│   └─ 交叉编译为 .deb + .cvimodel
│
├─ reCamera 应用 (Node-RED) → recamera_nodered
│   └─ 导出 flow.json
│
├─ Linux 设备 DEB 包 → ssh_deb
│   └─ 打包 .deb + systemd service
│
├─ Home Assistant 自定义集成 → ha_integration
│   └─ 准备 custom_components/<domain>/ 目录
│
├─ 本地脚本/服务 → script
│   └─ 写启动脚本 + 配置模板
│
├─ 需要人工操作（无法自动化） → manual
│   └─ 写清楚图文步骤
│
└─ 视频/数据预览 → preview
    └─ 配置 RTSP/MQTT 地址模板
```

---

## 输出清单

完成后确认以下交付物：

- [ ] `solution.yaml` — 方案配置，preset ID 与 guide.md 一致
- [ ] `description.md` + `description_zh.md` — 四段式介绍，术语通俗化
- [ ] `guide.md` + `guide_zh.md` — 中英文结构一致，所有步骤有故障排查
- [ ] `gallery/` — 封面图、架构图、步骤截图、Demo 视频
- [ ] `devices/` — 设备配置文件（如有 docker_deploy 类型步骤）
- [ ] 中英文 Preset/Step/Target ID 完全一致
- [ ] 每个步骤已验证可复现
