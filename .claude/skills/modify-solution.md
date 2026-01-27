# Skill: 修改现有方案

## 常见修改任务

### 1. 修改方案名称

**文件**: `solutions/[id]/solution.yaml`

```yaml
name: New English Name
name_zh: 新中文名称
```

### 2. 修改方案摘要

**文件**: `solutions/[id]/solution.yaml`

```yaml
intro:
  summary: New English summary
  summary_zh: 新中文摘要
```

### 3. 修改详细介绍

**文件**:
- `solutions/[id]/intro/description.md` (英文)
- `solutions/[id]/intro/description_zh.md` (中文)

**注意**: 不要写 H1 标题，从 H2 开始

### 4. 添加/修改设备目录

**文件**: `solutions/[id]/solution.yaml`

```yaml
intro:
  device_catalog:
    device_id:
      name: Device Name
      name_zh: 设备名称
      image: intro/gallery/device.png
      product_url: https://...
      description: Device description
      description_zh: 设备描述
```

### 5. 添加合作伙伴

**文件**: `solutions/[id]/solution.yaml`

```yaml
intro:
  partners:
    - name: Partner Name
      name_zh: 合作伙伴名称
      logo: intro/partners/logo.png
      regions:
        - 地区1
      regions_en:
        - Region1
      contact: email@example.com
      website: https://...
```

### 6. 修改/添加 Preset

**文件**: `solutions/[id]/solution.yaml`

```yaml
intro:
  presets:
    - id: new_preset
      name: New Preset
      name_zh: 新套餐
      description: Description
      description_zh: 描述
      badge: Recommended
      badge_zh: 推荐
      device_groups:
        - id: main_device
          name: Main Device
          type: single
          options:
            - device_ref: device_id
          default: device_id
      architecture_image: intro/gallery/architecture.png
      links:
        wiki: https://wiki.seeedstudio.com/...
      # 该 preset 的完整部署步骤
      devices:
        - id: step1
          name: Step 1
          name_zh: 步骤 1
          type: manual
          required: true
          section:
            title: Step Title
            title_zh: 步骤标题
            description_file: deploy/sections/step1.md
            description_file_zh: deploy/sections/step1_zh.md
```

### 7. 修改部署步骤

> **重要**：从 v1.1 开始，部署步骤定义在 `intro.presets[].devices` 中，不再使用 `deployment.devices`。

**文件**: `solutions/[id]/solution.yaml`

修改特定 preset 的部署步骤：

```yaml
intro:
  presets:
    - id: preset_id
      devices:
        # 添加新步骤
        - id: new_step
          name: New Step
          name_zh: 新步骤
          type: docker_deploy  # manual | esp32_usb | docker_deploy | preview
          required: true
          config_file: devices/config.yaml
          section:
            title: Step Title
            title_zh: 步骤标题
            description_file: deploy/sections/new_step.md
            description_file_zh: deploy/sections/new_step_zh.md
            troubleshoot_file: deploy/sections/new_step_troubleshoot.md
          targets:
            local:
              name: Local Deployment
              name_zh: 本机部署
              default: true
              config_file: devices/local.yaml
              section:
                description_file: deploy/sections/step_local.md
            remote:
              name: Remote Deployment
              name_zh: 远程部署
              config_file: devices/remote.yaml
              section:
                description_file: deploy/sections/step_remote.md
```

### 8. 修改部署步骤说明

**文件**:
- `solutions/[id]/deploy/sections/[step]_zh.md`
- `solutions/[id]/deploy/sections/[step].md`

**简化原则**:
- 自动部署类型：只写部署后需要用户操作的内容
- 手动步骤类型：写清楚用户需要执行的步骤

### 9. 调整步骤顺序

直接调整 preset.devices 数组中的元素顺序：

```yaml
intro:
  presets:
    - id: preset_id
      devices:
        - id: step1    # 第一个执行
        - id: step2    # 第二个执行
        - id: step3    # 第三个执行
```

---

## 应用级修改

### 修改应用标题

1. **i18n.js**: `frontend/src/modules/i18n.js`
   ```javascript
   en: { app: { title: 'English Title' } },
   zh: { app: { title: '中文标题' } }
   ```

2. **index.html**: `frontend/index.html`
   ```html
   <title>Title</title>
   <span class="brand" data-i18n="app.title">Title</span>
   ```

3. **main.js**: `frontend/src/main.js`
   ```javascript
   document.title = `${t(titleKey)} - Title`;
   ```

4. **settings.js**: `frontend/src/pages/settings.js`
   ```javascript
   <strong>Title</strong>
   ```

5. **删除旧构建**: `rm -rf frontend/dist`

### 修改侧边栏宽度

**文件**: `frontend/design-system/components.css`

```css
.sidebar {
  width: 260px;  /* 默认 240px */
}
```

### 修改按钮样式

**文件**: `frontend/design-system/components.css`

```css
.btn-deploy-hero {
  @apply py-3 px-8 rounded-lg ...;
  min-width: 180px;
}
```

### 添加新的 UI 文本

1. **添加翻译**: `frontend/src/modules/i18n.js`
   ```javascript
   en: { section: { newKey: 'English text' } },
   zh: { section: { newKey: '中文文本' } }
   ```

2. **使用翻译**:
   - JS 中: `t('section.newKey')`
   - HTML 中: `data-i18n="section.newKey"`

---

## 迁移旧方案到新结构

如果现有方案使用 `show_when` 条件，需要迁移到新的 `preset.devices` 结构：

### 旧结构（已废弃）

```yaml
deployment:
  devices:
    - id: step1
      show_when:
        preset: preset_a
    - id: step2
      show_when:
        preset: [preset_a, preset_b]
    - id: step3
      # 无 show_when，所有 preset 都显示
  order:
    - step1
    - step2
    - step3
```

### 新结构（推荐）

```yaml
intro:
  presets:
    - id: preset_a
      devices:
        - id: step1
          # ... 完整配置（不需要 show_when）
        - id: step2
          # ... 完整配置
        - id: step3
          # ... 完整配置

    - id: preset_b
      devices:
        - id: step2
          # ... 完整配置
        - id: step3
          # ... 完整配置

deployment:
  devices: []
  order: []
```

### 迁移步骤

1. 读取 `deployment.devices` 中的所有设备定义
2. 根据 `show_when.preset` 条件，将设备分配到对应的 preset
3. 无 `show_when` 的设备复制到所有 preset
4. 删除 `show_when` 字段
5. 设置 `deployment.devices: []` 和 `deployment.order: []`

---

## 调试技巧

### 页面显示旧内容

```bash
rm -rf frontend/dist
# 重启 dev.sh
```

### 中文内容显示英文

检查 API 调用是否传递了 `lang` 参数:
```javascript
solutionsApi.get(id, i18n.locale)  // 正确
solutionsApi.get(id)               // 错误，默认英文
```

### 图片不显示

1. 检查图片路径是否正确
2. 检查图片是否存在于 `solutions/[id]/` 目录下
3. API 会自动转换路径: `intro/gallery/x.png` → `/api/solutions/[id]/assets/intro/gallery/x.png`

### 切换 preset 后设备列表不变

检查 preset 是否正确配置了 `devices` 列表：
```yaml
intro:
  presets:
    - id: preset_id
      devices:  # 确保此字段存在且有内容
        - id: step1
          ...
```

---

## 参考文档

- 完整配置指南：`docs/solution-configuration-guide.md`
- 文案编写规范：`.claude/skills/solution-copywriting/SKILL.md`
