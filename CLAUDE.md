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
│   │   │   └── router.js       # 路由
│   │   └── pages/              # 页面组件
│   │       ├── solutions.js    # 方案列表
│   │       ├── solution-detail.js  # 方案详情
│   │       └── deploy.js       # 部署页面
│   └── design-system/          # 设计系统
│       └── components.css      # 组件样式
├── provisioning_station/       # 后端服务
│   ├── routers/
│   │   └── solutions.py        # 方案 API
│   └── services/
│       └── solution_manager.py # 方案管理
└── solutions/                  # 方案配置目录
    └── [solution_id]/          # 单个方案
        ├── solution.yaml       # 方案配置
        ├── intro/              # 介绍页内容
        │   ├── description.md
        │   ├── description_zh.md
        │   └── gallery/        # 图片资源
        └── deploy/             # 部署页内容
            ├── guide.md
            ├── guide_zh.md
            └── sections/       # 部署步骤说明
```

---

## 从 Wiki 文档创建新方案

### 步骤 1: 创建方案目录结构

```bash
solutions/
└── your_solution_id/
    ├── solution.yaml
    ├── intro/
    │   ├── description.md
    │   ├── description_zh.md
    │   └── gallery/
    │       └── (图片文件)
    └── deploy/
        ├── guide.md
        ├── guide_zh.md
        └── sections/
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

  # Markdown 详细介绍文件
  description_file: intro/description.md
  description_file_zh: intro/description_zh.md

  # 封面图片
  cover_image: intro/gallery/cover.png

  # 图库（可选）
  gallery:
    - type: image
      src: intro/gallery/demo1.png
      caption: Demo screenshot
      caption_zh: 演示截图

  # 分类和标签
  category: voice_ai  # 或 sensing, automation 等
  tags:
    - iot
    - watcher

  # 所需设备
  required_devices:
    - name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: intro/gallery/watcher.png
      purchase_url: https://www.seeedstudio.com/...
      description: AI-powered voice assistant
      description_zh: AI 语音助手

  # 统计信息
  stats:
    difficulty: beginner  # beginner | intermediate | advanced
    estimated_time: 30min
    deployed_count: 0
    likes_count: 0

  # 外部链接
  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

  # 部署合作伙伴（可选）
  partners:
    - name: Partner Name
      name_zh: 合作伙伴名称
      regions:
        - 广东省
      regions_en:
        - Guangdong
      contact: email@example.com

deployment:
  # 部署指南（显示在部署页顶部）
  guide_file: deploy/guide.md
  guide_file_zh: deploy/guide_zh.md

  # 部署设备/步骤
  devices:
    - id: step1
      name: Step Name
      name_zh: 步骤名称
      type: docker_local  # docker_local | esp32_usb | script | manual
      required: true
      section:
        title: Step Title
        title_zh: 步骤标题
        description_file: deploy/sections/step1.md
        description_file_zh: deploy/sections/step1_zh.md

  # 部署顺序
  order:
    - step1
    - step2
```

### 步骤 3: 编写 Markdown 内容

#### 介绍页 Markdown 规范

**文件**: `intro/description.md` / `intro/description_zh.md`

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

**文件**: `deploy/guide.md` / `deploy/guide_zh.md`

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
| `/api/solutions?lang=zh` | GET | 获取方案列表 |
| `/api/solutions/{id}?lang=zh` | GET | 获取方案详情 |
| `/api/solutions/{id}/deployment?lang=zh` | GET | 获取部署信息 |
| `/api/solutions/{id}/assets/{path}` | GET | 获取静态资源 |

**注意**: `lang` 参数控制返回内容的语言 (`en` 或 `zh`)

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
