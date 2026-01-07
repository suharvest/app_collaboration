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

### 4. 添加/修改设备

**文件**: `solutions/[id]/solution.yaml`

```yaml
intro:
  required_devices:
    - name: Device Name
      name_zh: 设备名称
      image: intro/gallery/device.png
      purchase_url: https://...
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

### 6. 修改部署步骤说明

**文件**:
- `solutions/[id]/deploy/sections/[step]_zh.md`
- `solutions/[id]/deploy/sections/[step].md`

**简化原则**:
- 自动部署类型：只写部署后需要用户操作的内容
- 手动步骤类型：写清楚用户需要执行的步骤

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
