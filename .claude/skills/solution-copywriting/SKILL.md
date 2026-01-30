---
name: optimize-solution
description: 优化 IoT 解决方案文案。检查并改进 solutions/ 目录下的介绍页和部署页文案，确保非技术用户能理解。使用场景：优化文案、检查术语、修复文案问题。
argument-hint: "<solution_id> [修改方向]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Solution Copywriting Skill

## 调用方式

```
/optimize-solution smart_warehouse                    # 全面检查
/optimize-solution smart_warehouse 介绍页术语太专业    # 指定修改方向
/optimize-solution smart_warehouse 部署步骤不清晰
/optimize-solution smart_warehouse 添加故障排查表格
```

## 参数说明

- `$0` = solution_id（必填）
- `$1...` = 修改方向（可选，自然语言描述）

## 执行流程

**Step 1**: 读取方案文件
- `solutions/$0/solution.yaml`
- `solutions/$0/intro/description_zh.md`
- `solutions/$0/deploy/sections/*.md`

**如果指定了修改方向 (`$1`)**: 优先按用户指定方向修改，跳过无关检查项。

**Step 2**: 介绍页检查（对照下方「一、介绍页文案标准」）
- [ ] 有「这个方案能帮你做什么」段落？
- [ ] 有「核心价值」表格？
- [ ] 有「适用场景」示例？
- [ ] 有「使用须知」限制说明？
- [ ] 专业术语已替换？

**Step 3**: 部署页检查（对照下方「三、部署页文案标准」）
- [ ] description 只包含准备工作？
- [ ] troubleshoot 包含故障排查？
- [ ] 无"完成后"内容错位？

**Step 4**: 输出改进报告
- 按 P0/P1/P2 分类问题
- 提供修改建议或直接修改

---

## 概述

本 Skill 用于创建或优化 `solutions/` 目录下的解决方案文案，确保：
- 非技术用户能在 30 秒内理解方案价值
- 部署步骤清晰可执行，不卡壳、不出错
- 用词通俗易懂，避免专业术语

---

## 一、介绍页文案标准

### 目标
帮助非技术用户在 30 秒内理解：**这个方案解决什么问题？对我有什么好处？**

### 文件位置
- 英文：`solutions/[id]/intro/description.md`
- 中文：`solutions/[id]/intro/description_zh.md`

### 结构模板（必须包含以下 4 个部分）

```markdown
## 这个方案能帮你做什么

[用 1-2 句话，用通俗语言描述痛点和解决方案]

示例：
- ✓ "小智助手虽然能听懂你说话，但看不见你的脸——它不知道是谁在说话。这个方案给小智装上'眼睛'，让它认识家人朋友。"
- ✗ "本方案通过集成视觉识别模块实现多模态人机交互能力增强。"

## 核心价值

用 3-4 个要点说明好处，每个要点：
- 用「动词 + 具体结果」的格式
- 附带可量化的指标或具体场景

| 好处 | 具体说明 |
|------|---------|
| 省时间 | 查库存只需说一句话，不用放下手里的活去电脑前操作 |
| 省成本 | 单套设备 ¥XXX，比传统方案便宜 60% |
| 易上手 | 3 步完成部署，不需要写代码 |

## 适用场景

列出 3-4 个具体应用场景，每个场景包含：
- **场景名称**：一句话描述
- **使用示例**：具体的操作或对话

| 场景 | 怎么用 |
|------|--------|
| 家庭助手 | 说"记住我的脸，我叫小明"，下次小智会主动打招呼 |
| 仓库管理 | 说"A3 货架还有多少货"，叉车司机不用下车查电脑 |

## 使用须知

列出用户需要了解的限制条件：
- 硬件要求（需要什么设备）
- 环境要求（光线、网络等）
- 容量限制（最多支持多少人/设备）

示例：
- 最多记住 20 张人脸
- 需要充足光线，暗处识别率会下降
- 正脸效果最佳，侧脸可能认不出
```

---

## 二、术语通俗化对照表

编写文案时，**必须**将专业术语替换为通俗表达：

| 专业术语 | 通俗替代 |
|---------|---------|
| ASR 语音识别 | 听懂你说的话 |
| TTS 语音合成 | 说话给你听 |
| 推理/Inference | 分析判断 |
| 边缘计算 | 本地处理（不需要联网） |
| API 调用 | 连接到你的系统 |
| Docker 容器 | 一键部署包 |
| MQTT 消息 | 数据传输 |
| 隐私模糊处理 | 自动打码保护隐私 |
| 热力图 | 人流分布图 |
| OPC-UA | 工业设备通讯 |
| LLM/大语言模型 | AI 对话能力 |
| 多模态 | 能看能听能说 |
| 向量数据库 | 记忆存储 |
| RAG | 根据资料回答问题 |
| MCP 协议 | 设备连接方式 |
| 串口/Serial | USB 连接 |
| 固件/Firmware | 设备内部程序 |
| 烧录 | 写入程序 |

---

## 三、部署页文案标准

### 目标
让非技术用户按步骤操作，**不卡壳、不出错、不迷路**。

### 文件结构

```
deploy/
├── guide_zh.md          # 部署总览（必须）
├── guide.md             # 英文版
└── sections/
    ├── step1_zh.md      # 步骤 1 详情
    ├── step1.md         # 英文版
    └── troubleshoot_zh.md  # 常见问题（可选）
```

### guide_zh.md 模板

```markdown
## 开始之前

### 你需要准备

| 类别 | 准备内容 | 说明 |
|------|---------|------|
| 硬件 | SenseCAP Watcher | 主控设备 |
| 硬件 | USB-C 数据线 | 用于连接电脑 |
| 软件 | Chrome 浏览器 | 用于烧录固件 |
| 账号 | SenseCraft 账号 | [点此注册](链接) |

### 部署流程预览

```
[硬件连接] → [固件烧录] → [服务部署] → [测试验收]
   5分钟        10分钟        5分钟        5分钟
```

## 部署完成后

[简要说明如何验证部署成功，以及日常使用入口]
```

### 步骤页布局说明

**重要**：页面分为三个区域，内容需要放在正确的位置。

```
┌─────────────────────────────────────────┐
│  description 区域（部署按钮上方）          │  ← 只写准备工作
│  - 连接说明                              │
│  - 注意事项                              │
├─────────────────────────────────────────┤
│  [ 🚀 开始部署 ]  ← 部署按钮              │  ← 系统自动渲染
├─────────────────────────────────────────┤
│  troubleshoot 区域（部署按钮下方）         │  ← 故障排查内容
│  - 遇到问题？                            │
│  - 常见问题表格                          │
└─────────────────────────────────────────┘
```

### solution.yaml section 配置

> **注意**：从 v1.1 开始，部署步骤定义在 `intro.presets[].devices` 中。

```yaml
intro:
  presets:
    - id: preset_id
      devices:
        - id: flash_firmware
          name: Flash Firmware
          name_zh: 烧录固件
          type: esp32_usb
          required: true
          config_file: devices/esp32.yaml
          section:
            title: 烧录固件
            title_zh: 烧录固件
            # 部署按钮上方的内容（准备工作）
            description_file: deploy/sections/flash.md
            description_file_zh: deploy/sections/flash_zh.md
            # 部署按钮下方的内容（故障排查）
            troubleshoot_file: deploy/sections/flash_troubleshoot.md
            troubleshoot_file_zh: deploy/sections/flash_troubleshoot_zh.md
```

### description 文件内容（部署按钮上方）

只写**点击部署前**需要知道的信息：

```markdown
### 连接设备

1. 用 USB-C 线连接 Watcher 到电脑
2. 在上方选择串口（选 wchusbserial 开头的）
```

### troubleshoot 文件内容（部署按钮下方）

写**部署过程中或失败后**的排查指南：

```markdown
### 遇到问题？

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 烧录失败 | 重新插拔设备再试 |
```

### 错误示范

**不要**把故障排查放在 description 文件中：

```markdown
### 连接设备
1. 用 USB-C 线连接 Watcher

### 遇到问题？        ← ❌ 错误！应该放在 troubleshoot 文件
| 问题 | 解决方法 |
```

### "完成后"内容放在哪里？

**solution.yaml 的 post_deployment**：
```yaml
post_deployment:
  success_message_zh: |
    部署完成！设备会自动重启，屏幕显示小智表情即为成功。
```

### 步骤顺序原则

**正确顺序**：
1. 物理连接（插线、摆放设备）
2. 固件/软件准备（烧录、安装）
3. 配置设置（账号、参数）
4. 启动服务（一键部署）
5. 测试验收（功能验证）
6. 问题排查（可选）

**常见错误**：
- 先讲部署命令，再讲插线方法
- 把问题排查放在步骤中间
- 多个步骤混在一起讲
- 把"完成后"的提示放在部署按钮上方

---

## 四、质量检查清单

### 介绍页检查

- [ ] **30 秒测试**：非技术人员能否在 30 秒内说出"这是干什么的"
- [ ] **价值明确**：每个核心价值都有具体数字或场景支撑
- [ ] **场景具体**：每个场景都有真实的使用示例
- [ ] **限制透明**：明确告知用户硬件要求和能力边界
- [ ] **无专业术语**：或专业术语都有通俗解释

### 部署页检查

- [ ] **准备清单完整**：用户知道需要准备什么
- [ ] **步骤可执行**：每一步都是明确的动作，不是概念描述
- [ ] **顺序合理**：先物理后软件，先准备后操作
- [ ] **成功可验证**：每步都有检查方法
- [ ] **问题可解决**：常见问题都有对应方案
- [ ] **无"完成后"错位**：section 中不包含部署后的提示

---

## 五、最佳范例

### 介绍页范例：xiaozhi_face_recognition

**优点**：
1. 痛点陈述有吸引力："看不见人脸，不知道是谁"
2. 解决方案用比喻："给小智装上'眼睛'"
3. 使用示例是自然语言对话
4. 限制条件坦诚透明

### 部署页范例：recamera_retail_heatmap

**优点**：
1. 故障排除表格完整
2. 步骤有检查清单
3. 技术规格用表格呈现
4. section 内容不包含"完成后"提示

---

## 六、使用方法

### 创建新方案文案

1. 复制目录结构：
   ```bash
   cp -r solutions/recamera_retail_heatmap solutions/your_solution_id
   ```

2. 按本规范编写 `solution.yaml`

3. 按模板编写介绍页和部署页

4. 使用检查清单自检

### 优化现有方案文案

1. 读取现有文案
2. 对照检查清单找出问题
3. 按规范修改
4. 重点检查：
   - 术语是否通俗化
   - section 是否有"完成后"错位
   - 是否有具体场景和示例

---

## 七、常见文案问题及修复

### 高优先级问题（P0）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 术语堆砌 | 首段出现 3+ 专业术语 | 用「术语通俗化对照表」替换 |
| 价值模糊 | 无法 30 秒说清"干什么用" | 重写「这个方案能帮你做什么」段落 |
| 步骤缺失 | 用户卡在某步不知道下一步 | 补充 wiring.steps 或 description |

### 中优先级问题（P1）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 缺接线图 | 硬件连接方式不清晰 | 添加 wiring.image |
| 完成后错位 | section 中包含"部署成功后"内容 | 移到 post_deployment |
| 缺故障排查 | 部署失败后无指引 | 添加 troubleshoot_file |

### 低优先级问题（P2）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 场景抽象 | 只说功能，不说具体怎么用 | 添加对话示例或操作流程 |
| 限制不透明 | 不告知能力边界 | 补充「使用须知」段落 |

### 优秀方案参考

- `recamera_heatmap_grafana` - 结构完整，targets 配置规范
- `smart_space_assistant` - preset 分离清晰，wiring 说明详细

---

## 八、配置结构说明

### 1. device_catalog（设备目录）

在 `intro.device_catalog` 中定义方案使用的所有设备，供 presets 引用：

```yaml
intro:
  device_catalog:
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: intro/gallery/watcher.svg
      product_url: https://www.seeedstudio.com/sensecap-watcher
      description: AI-powered voice assistant
      description_zh: AI 语音助手

    recomputer_r1100:
      name: reComputer R1100
      name_zh: reComputer R1100
      image: intro/gallery/recomputer.svg
      product_url: https://www.seeedstudio.com/recomputer-r1100
      description: Edge gateway for services
      description_zh: 边缘网关
```

### 2. presets（部署套餐）

每个 preset 是一个完整的部署方案，包含设备选择和部署步骤：

```yaml
intro:
  presets:
    - id: cloud_mode
      name: Cloud Mode
      name_zh: 云端模式
      badge: Recommended           # 角标（可选）
      badge_zh: 推荐
      description: Use cloud services
      description_zh: 使用云服务
      architecture_image: intro/gallery/arch.svg  # 架构图（可选）
      links:                       # 相关链接
        wiki: https://wiki.seeedstudio.com/...
        github: https://github.com/...

      # 设备组选择（用户在页面上选择设备）
      device_groups:
        - id: voice_assistant
          name: Voice Assistant
          name_zh: 语音助手
          type: single             # single | multiple
          required: true
          options:
            - device_ref: sensecap_watcher  # 引用 device_catalog
          default: sensecap_watcher

      # preset 级别的部署指南
      section:
        title: Cloud Deployment Guide
        title_zh: 云端部署指南
        description_file: deploy/sections/cloud_guide.md
        description_file_zh: deploy/sections/cloud_guide_zh.md

      # 部署步骤列表
      devices:
        - id: step1
          name: Step Name
          name_zh: 步骤名称
          type: docker_deploy      # 见下方类型说明
          required: true
          config_file: devices/config.yaml
          section:
            title: Step Title
            title_zh: 步骤标题
          targets: ...             # 见下方 targets 说明
```

**设备类型 (type)**：
- `manual` - 手动步骤（仅显示说明）
- `docker_deploy` - Docker 容器部署
- `esp32_usb` - ESP32 USB 烧录
- `himax_usb` - Himax 芯片烧录
- `recamera_cpp` - reCamera C++ 应用部署
- `recamera_nodered` - reCamera Node-RED 部署
- `script` - 脚本执行
- `preview` - 预览功能

### 3. targets（部署目标）

支持同一步骤部署到不同目标（本机/远程）：

```yaml
devices:
  - id: backend
    name: Deploy Backend
    name_zh: 部署后端
    type: docker_deploy
    section:
      title: Deploy Backend Services
      title_zh: 部署后端服务
    targets:
      local:
        name: Local Deployment
        name_zh: 本机部署
        description: Deploy on this computer
        description_zh: 部署到当前电脑
        default: true              # 默认选项
        config_file: devices/backend_local.yaml
        section:
          description_file: deploy/sections/backend_local.md
          description_file_zh: deploy/sections/backend_local_zh.md
          troubleshoot_file: deploy/sections/backend_troubleshoot.md
          troubleshoot_file_zh: deploy/sections/backend_troubleshoot_zh.md
          wiring: ...              # 见下方 wiring 说明

      remote:
        name: Remote Deployment
        name_zh: 远程部署
        description: Deploy via SSH
        description_zh: 通过 SSH 部署
        config_file: devices/backend_remote.yaml
        section:
          description_file: deploy/sections/backend_remote.md
          description_file_zh: deploy/sections/backend_remote_zh.md
```

### 4. wiring（接线说明）

在 section 中添加可视化接线指引：

```yaml
section:
  description_file: deploy/sections/step.md
  description_file_zh: deploy/sections/step_zh.md
  wiring:
    image: intro/gallery/wiring.svg   # 接线示意图
    steps:
      - Connect device to computer via USB-C
      - Select the serial port
      - Click Deploy button
    steps_zh:
      - 用 USB-C 线连接设备到电脑
      - 选择串口
      - 点击部署按钮
```

### 5. post_deployment（部署完成后）

定义部署成功后的提示和后续步骤：

```yaml
deployment:
  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps:
      - title: Access Web Interface
        title_zh: 访问 Web 界面
        action: open_url
        url: "http://localhost:8080"
      - title: View Documentation
        title_zh: 查看文档
        description: Learn more about the features
        description_zh: 了解更多功能
        action: open_url
        url: "https://wiki.seeedstudio.com/..."
```

### 6. 完整配置骨架

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
  cover_image: intro/gallery/cover.svg
  gallery: [...]
  category: voice_ai
  tags: [...]

  device_catalog:
    device_id: { ... }

  presets:
    - id: preset_id
      name: ...
      device_groups: [...]
      section: { ... }
      devices: [...]

  stats:
    difficulty: beginner | intermediate | advanced
    estimated_time: 30min
    deployed_count: 0
    likes_count: 0

  links:
    wiki: https://...
    github: https://...

  partners: [...]    # 可选

deployment:
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md
  selection_mode: sequential
  devices: []        # 保持为空
  order: []          # 保持为空
  post_deployment:
    success_message_file: deploy/success.md
    success_message_file_zh: deploy/success_zh.md
    next_steps: [...]
```

### 参考文档

- 完整配置指南：`docs/solution-configuration-guide.md`
- 从 Wiki 创建方案：`.claude/skills/add-solution-from-wiki.md`
