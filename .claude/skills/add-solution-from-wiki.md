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
- 部署步骤
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

关键字段映射：

| Wiki 内容 | YAML 字段 |
|----------|----------|
| 标题 | `name` / `name_zh` |
| 简介第一段 | `summary` / `summary_zh` |
| 硬件清单 | `required_devices` |
| 难度说明 | `stats.difficulty` |
| 预计时间 | `stats.estimated_time` |

### 5. 转换 Markdown 内容

#### Wiki → 介绍页 (description.md)

**删除**:
- H1 标题（页面已有）
- 目录导航
- 硬件购买链接（移到 required_devices）
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
3. 生成 solution.yaml
4. 转换 markdown 内容
5. 提示用户补充图片
