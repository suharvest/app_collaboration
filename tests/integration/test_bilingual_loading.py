"""
Integration tests for bilingual markdown loading.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from provisioning_station.services.markdown_parser import (
    parse_bilingual_markdown,
    parse_deployment_guide,
    ParseResult,
)


@pytest.fixture
def temp_solution_dir():
    """Create a temporary solution directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


class TestBilingualMarkdownLoading:
    """Tests for loading bilingual markdown content."""

    def test_load_english_from_bilingual(self):
        """Load English content from a bilingual file."""
        content = """<!-- @lang:en -->

# English Title

This is English content.

<!-- @lang:zh -->

# 中文标题

这是中文内容。
"""
        result = parse_bilingual_markdown(content, "en")
        assert "English Title" in result
        assert "English content" in result
        assert "中文" not in result

    def test_load_chinese_from_bilingual(self):
        """Load Chinese content from a bilingual file."""
        content = """<!-- @lang:en -->

# English Title

This is English content.

<!-- @lang:zh -->

# 中文标题

这是中文内容。
"""
        result = parse_bilingual_markdown(content, "zh")
        assert "中文标题" in result
        assert "中文内容" in result
        assert "English" not in result

    def test_fallback_to_english_when_no_chinese(self):
        """Fall back to English when Chinese is not available."""
        content = """<!-- @lang:en -->

# English Only

This file only has English content.
"""
        result = parse_bilingual_markdown(content, "zh")
        assert "English Only" in result

    def test_fallback_to_chinese_when_no_english(self):
        """Fall back to Chinese when English is not available."""
        content = """<!-- @lang:zh -->

# 仅中文

此文件仅包含中文内容。
"""
        result = parse_bilingual_markdown(content, "en")
        assert "仅中文" in result

    def test_no_markers_treats_as_english(self):
        """Content without markers is treated as English."""
        content = """# Plain Content

No language markers here.
"""
        en_result = parse_bilingual_markdown(content, "en")
        zh_result = parse_bilingual_markdown(content, "zh")

        assert "Plain Content" in en_result
        # Fallback behavior - returns English when zh not found
        assert "Plain Content" in zh_result


class TestDeploymentGuideParsing:
    """Tests for parsing deployment guide structure."""

    def test_parse_simple_steps(self):
        """Parse a guide with simple steps."""
        content = """<!-- @lang:en -->

# Deployment Guide

Follow these steps.

## Step 1: Install Docker {#docker type=docker_local required=true}

Install Docker Desktop.

### Prerequisites

- macOS or Windows

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Won't start | Restart computer |

---

## Step 2: Configure {#configure type=manual required=false}

Configure the system.

<!-- @lang:zh -->

# 部署指南

按照以下步骤操作。

## 步骤 1: 安装 Docker {#docker type=docker_local required=true}

安装 Docker Desktop。

### 前置条件

- macOS 或 Windows

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 无法启动 | 重启电脑 |

---

## 步骤 2: 配置 {#configure type=manual required=false}

配置系统。
"""
        result = parse_deployment_guide(content)

        assert not result.has_errors
        assert len(result.steps) == 2

        docker_step = result.steps[0]
        assert docker_step.id == "docker"
        assert docker_step.type == "docker_local"
        assert docker_step.required is True
        assert "Install Docker" in docker_step.section.description
        assert "安装 Docker" in docker_step.section.description_zh
        assert "Won't start" in docker_step.section.troubleshoot
        assert "无法启动" in docker_step.section.troubleshoot_zh

        config_step = result.steps[1]
        assert config_step.id == "configure"
        assert config_step.type == "manual"
        assert config_step.required is False

    def test_parse_with_success_section(self):
        """Parse a guide with success/completion section."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#deploy type=manual required=true}

Deploy the service.

# Deployment Complete

Congratulations! All done.

## Next Steps

1. Open the web interface
2. Configure settings

<!-- @lang:zh -->

## 步骤 1: 部署 {#deploy type=manual required=true}

部署服务。

# 部署完成

恭喜！全部完成。

## 下一步

1. 打开网页界面
2. 配置设置
"""
        result = parse_deployment_guide(content)

        assert not result.has_errors
        assert result.success is not None
        assert "Congratulations" in result.success.content_en
        assert "恭喜" in result.success.content_zh
        assert "Next Steps" in result.success.content_en

    def test_parse_with_presets(self):
        """Parse a guide with preset groupings."""
        content = """<!-- @lang:en -->

# Overview

Choose your deployment method.

## Preset: Cloud Solution {#cloud}

Use cloud services for quick setup.

## Step 1: Deploy Backend {#backend type=docker_deploy required=true config=devices/docker.yaml}

Deploy the backend service.

## Preset: Edge Computing {#edge}

Deploy on local edge devices.

## Step 1: Setup Edge {#edge_setup type=script required=true}

Set up edge computing.

<!-- @lang:zh -->

# 概述

选择部署方式。

## 套餐: 云方案 {#cloud}

使用云服务快速部署。

## 步骤 1: 部署后端 {#backend type=docker_deploy required=true config=devices/docker.yaml}

部署后端服务。

## 套餐: 边缘计算 {#edge}

部署到本地边缘设备。

## 步骤 1: 设置边缘 {#edge_setup type=script required=true}

设置边缘计算。
"""
        result = parse_deployment_guide(content)

        assert not result.has_errors
        assert len(result.presets) == 2

        cloud_preset = result.presets[0]
        assert cloud_preset.id == "cloud"
        assert cloud_preset.name == "Cloud Solution"
        assert cloud_preset.name_zh == "云方案"
        assert len(cloud_preset.steps) == 1
        assert cloud_preset.steps[0].id == "backend"
        assert cloud_preset.steps[0].config_file == "devices/docker.yaml"

        edge_preset = result.presets[1]
        assert edge_preset.id == "edge"
        assert len(edge_preset.steps) == 1
        assert edge_preset.steps[0].id == "edge_setup"

    def test_parse_errors_for_invalid_type(self):
        """Return errors for invalid step type."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#deploy type=invalid_type required=true}

This step has an invalid type.
"""
        result = parse_deployment_guide(content)

        assert result.has_errors
        assert len(result.errors) == 1
        assert "invalid_type" in result.errors[0].message.lower()

    def test_parse_errors_for_duplicate_id(self):
        """Return errors for duplicate step IDs."""
        content = """<!-- @lang:en -->

## Step 1: First {#same_id type=manual required=true}

First step.

## Step 2: Second {#same_id type=manual required=true}

Second step with same ID.
"""
        result = parse_deployment_guide(content)

        assert result.has_errors
        assert any("duplicate" in e.message.lower() for e in result.errors)

    def test_warnings_for_missing_translation(self):
        """Generate warnings when translation is missing."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#deploy type=manual required=true}

English only step.
"""
        result = parse_deployment_guide(content)

        assert not result.has_errors
        assert len(result.warnings) > 0
        assert any("translation" in w.message.lower() for w in result.warnings)

    def test_parse_with_wiring_section(self):
        """Parse step with wiring information."""
        content = """<!-- @lang:en -->

## Step 1: Connect Device {#connect type=esp32_usb required=true}

Connect the device.

### Wiring

![Diagram](gallery/wiring.png)

1. Connect USB cable
2. Press boot button
3. Check LED status

<!-- @lang:zh -->

## 步骤 1: 连接设备 {#connect type=esp32_usb required=true}

连接设备。

### 接线

![接线图](gallery/wiring.png)

1. 连接 USB 线
2. 按下启动按钮
3. 检查 LED 状态
"""
        result = parse_deployment_guide(content)

        assert not result.has_errors
        step = result.steps[0]
        assert step.section.wiring is not None
        assert step.section.wiring.image == "gallery/wiring.png"
        assert len(step.section.wiring.steps) == 3
        assert "USB cable" in step.section.wiring.steps[0]
        assert len(step.section.wiring.steps_zh) == 3
        assert "USB 线" in step.section.wiring.steps_zh[0]
