"""
Unit tests for the multilingual markdown parser.
"""

import pytest

from provisioning_station.services.markdown_parser import (
    ParseErrorType,
    _get_valid_step_types,
    extract_wiring,
    extract_wiring_multilang,
    parse_bilingual_markdown,
    parse_deployment_guide,
    parse_step_attributes,
    parse_subsections,
    split_by_language,
)


class TestSplitByLanguage:
    """Tests for split_by_language function."""

    def test_no_markers(self):
        """Content without markers returns as English."""
        content = "# Hello\n\nThis is content."
        en, zh = split_by_language(content)
        assert en == content.strip()
        assert zh == ""

    def test_english_only(self):
        """Content with only English marker."""
        content = """<!-- @lang:en -->
# Hello

English content here.
"""
        en, zh = split_by_language(content)
        assert "English content" in en
        assert zh == ""

    def test_chinese_only(self):
        """Content with only Chinese marker."""
        content = """<!-- @lang:zh -->
# 你好

中文内容。
"""
        en, zh = split_by_language(content)
        assert en == ""
        assert "中文内容" in zh

    def test_both_languages(self):
        """Content with both language markers."""
        content = """<!-- @lang:en -->
# Hello

English content here.

<!-- @lang:zh -->
# 你好

中文内容在这里。
"""
        en, zh = split_by_language(content)
        assert "English content" in en
        assert "中文内容" in zh
        assert "你好" not in en
        assert "Hello" not in zh

    def test_markers_with_extra_spaces(self):
        """Markers with extra whitespace."""
        content = """<!--  @lang:en  -->
English

<!--   @lang:zh   -->
Chinese
"""
        en, zh = split_by_language(content)
        assert "English" in en
        assert "Chinese" in zh


class TestParseStepAttributes:
    """Tests for parse_step_attributes function."""

    def test_simple_attributes(self):
        """Parse simple key=value pairs."""
        attrs = parse_step_attributes("type=docker_deploy required=true")
        assert attrs["type"] == "docker_deploy"
        assert attrs["required"] is True

    def test_false_boolean(self):
        """Parse false boolean value."""
        attrs = parse_step_attributes("required=false")
        assert attrs["required"] is False

    def test_path_value(self):
        """Parse path values."""
        attrs = parse_step_attributes("config=devices/docker.yaml")
        assert attrs["config"] == "devices/docker.yaml"

    def test_quoted_value(self):
        """Parse quoted values with spaces."""
        attrs = parse_step_attributes('name="My Step Name"')
        assert attrs["name"] == "My Step Name"

    def test_empty_string(self):
        """Empty string returns empty dict."""
        attrs = parse_step_attributes("")
        assert attrs == {}


class TestParseSubsections:
    """Tests for parse_subsections function."""

    def test_no_subsections(self):
        """Content without subsection headers."""
        content = """This is main content.

More content here.
"""
        result = parse_subsections(content)
        assert "main content" in result["main"]
        assert result["prerequisites"] == ""
        assert result["troubleshoot"] == ""

    def test_with_prerequisites(self):
        """Content with Prerequisites section."""
        content = """Main description.

### Prerequisites

- Item 1
- Item 2
"""
        result = parse_subsections(content)
        assert "Main description" in result["main"]
        assert "Item 1" in result["prerequisites"]

    def test_with_troubleshoot(self):
        """Content with Troubleshooting section."""
        content = """Main content.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Error | Fix it |
"""
        result = parse_subsections(content)
        assert "Main content" in result["main"]
        assert "Issue" in result["troubleshoot"]

    def test_chinese_headers(self):
        """Chinese subsection headers."""
        content = """主要内容。

### 前置条件

- 条件 1

### 故障排除

检查网络连接。
"""
        result = parse_subsections(content)
        assert "主要内容" in result["main"]
        assert "条件 1" in result["prerequisites"]
        assert "网络连接" in result["troubleshoot"]

    def test_all_subsections(self):
        """Content with all subsection types."""
        content = """Main content here.

### Prerequisites

Setup requirements.

### Wiring

![Diagram](image.png)

1. Connect cable
2. Power on

### Troubleshooting

Check connections.
"""
        result = parse_subsections(content)
        assert "Main content" in result["main"]
        assert "Setup requirements" in result["prerequisites"]
        assert "Connect cable" in result["wiring"]
        assert "Check connections" in result["troubleshoot"]


class TestExtractWiring:
    """Tests for extract_wiring function."""

    def test_with_image_and_steps(self):
        """Extract image and ordered list steps."""
        content = """![Wiring Diagram](gallery/wiring.png)

1. Connect USB cable
2. Power on the device
3. Check LED status
"""
        wiring = extract_wiring(content)
        assert wiring is not None
        assert wiring.image == "gallery/wiring.png"
        assert len(wiring.steps.get("en")) == 3
        assert "Connect USB cable" in wiring.steps.get("en")[0]

    def test_image_only(self):
        """Extract only image."""
        content = """![Architecture](arch.png)

Some text without numbered list.
"""
        wiring = extract_wiring(content)
        assert wiring is not None
        assert wiring.image == "arch.png"
        assert wiring.steps.get("en") == []

    def test_no_wiring_content(self):
        """No wiring information returns None."""
        content = "Just plain text without image or list."
        wiring = extract_wiring(content)
        assert wiring is None

    def test_bilingual_steps(self):
        """Extract steps from both languages using multilang."""
        en = """1. Connect cable
2. Check status
"""
        zh = """1. 连接线缆
2. 检查状态
"""
        wiring = extract_wiring_multilang({"en": en, "zh": zh})
        assert wiring is not None
        assert len(wiring.steps.get("en")) == 2
        assert len(wiring.steps.get("zh")) == 2
        assert "连接线缆" in wiring.steps.get("zh")[0]


class TestParseBilingualMarkdown:
    """Tests for parse_bilingual_markdown function."""

    def test_get_english(self):
        """Get English content from bilingual file."""
        content = """<!-- @lang:en -->
English text here.

<!-- @lang:zh -->
中文内容。
"""
        result = parse_bilingual_markdown(content, "en")
        assert "English text" in result
        assert "中文" not in result

    def test_get_chinese(self):
        """Get Chinese content from bilingual file."""
        content = """<!-- @lang:en -->
English text here.

<!-- @lang:zh -->
中文内容。
"""
        result = parse_bilingual_markdown(content, "zh")
        assert "中文内容" in result
        assert "English" not in result

    def test_fallback_to_english(self):
        """Fallback to English if Chinese not available."""
        content = """<!-- @lang:en -->
English only content.
"""
        result = parse_bilingual_markdown(content, "zh")
        assert "English only" in result


class TestParseDeploymentGuide:
    """Tests for parse_deployment_guide function."""

    def test_single_step(self):
        """Parse a single deployment step."""
        content = """<!-- @lang:en -->

## Step 1: Deploy Backend {#backend type=docker_deploy required=true}

Deploy the backend service.

### Prerequisites

- Docker installed

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port busy | Stop other services |

<!-- @lang:zh -->

## 步骤 1: 部署后端 {#backend type=docker_deploy required=true}

部署后端服务。

### 前置条件

- 已安装 Docker

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口占用 | 停止其他服务 |
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        assert len(result.steps) == 1

        step = result.steps[0]
        assert step.id == "backend"
        assert step.type == "docker_deploy"
        assert step.required is True
        assert "Deploy the backend" in step.section.description.get("en")
        assert "部署后端" in step.section.description.get("zh")
        assert "Port busy" in step.section.troubleshoot.get("en")
        assert "端口占用" in step.section.troubleshoot.get("zh")

    def test_multiple_steps(self):
        """Parse multiple deployment steps."""
        content = """<!-- @lang:en -->

## Step 1: Deploy Backend {#backend type=docker_deploy required=true}

Backend content.

---

## Step 2: Configure Platform {#platform type=manual required=true}

Platform content.

---

## Step 3: Demo {#demo type=preview required=false}

Demo content.

<!-- @lang:zh -->

## 步骤 1: 部署后端 {#backend type=docker_deploy required=true}

后端内容。

---

## 步骤 2: 配置平台 {#platform type=manual required=true}

平台内容。

---

## 步骤 3: 演示 {#demo type=preview required=false}

演示内容。
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        assert len(result.steps) == 3

        assert result.steps[0].id == "backend"
        assert result.steps[1].id == "platform"
        assert result.steps[2].id == "demo"
        assert result.steps[2].required is False

    def test_with_config_file(self):
        """Parse step with config file attribute."""
        content = """<!-- @lang:en -->

## Step 1: Deploy Service {#service type=docker_local required=true config=devices/docker.yaml}

Deploy with config.
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        assert result.steps[0].config_file == "devices/docker.yaml"

    def test_invalid_type_error(self):
        """Error on invalid step type."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#step1 type=invalid_type required=true}

Content.
"""
        result = parse_deployment_guide(content)
        assert result.has_errors
        assert any(e.error_type == ParseErrorType.INVALID_STEP_TYPE for e in result.errors)

    def test_missing_type_error(self):
        """Error on missing type attribute."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#step1 required=true}

Content.
"""
        result = parse_deployment_guide(content)
        assert result.has_errors
        assert any(e.error_type == ParseErrorType.MISSING_REQUIRED_FIELD for e in result.errors)

    def test_duplicate_step_id_error(self):
        """Error on duplicate step IDs."""
        content = """<!-- @lang:en -->

## Step 1: First {#same_id type=manual required=true}

First content.

## Step 2: Second {#same_id type=manual required=true}

Second content.
"""
        result = parse_deployment_guide(content)
        assert result.has_errors
        assert any(e.error_type == ParseErrorType.DUPLICATE_STEP_ID for e in result.errors)

    def test_missing_chinese_warning(self):
        """Warning when Chinese translation missing."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#step1 type=manual required=true}

English only content.
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        assert any("Chinese translation" in w.message for w in result.warnings)

    def test_with_overview(self):
        """Parse overview section at the top."""
        content = """<!-- @lang:en -->

# Deployment Guide

This is the overview section before any steps.

## Step 1: Deploy {#step1 type=manual required=true}

Step content.

<!-- @lang:zh -->

# 部署指南

这是步骤之前的概述部分。

## 步骤 1: 部署 {#step1 type=manual required=true}

步骤内容。
"""
        result = parse_deployment_guide(content)
        assert "overview section" in result.overview.get("en")
        assert "概述部分" in result.overview.get("zh")

    def test_with_success_section(self):
        """Parse success section at the end."""
        content = """<!-- @lang:en -->

## Step 1: Deploy {#step1 type=manual required=true}

Step content.

# Deployment Complete

Congratulations! All done.

## Next Steps

1. Open web interface
2. Configure settings

<!-- @lang:zh -->

## 步骤 1: 部署 {#step1 type=manual required=true}

步骤内容。

# 部署完成

恭喜！全部完成。

## 下一步

1. 打开网页界面
2. 配置设置
"""
        result = parse_deployment_guide(content)
        assert result.success is not None
        assert "Congratulations" in result.success.content.get("en")
        assert "恭喜" in result.success.content.get("zh")

    def test_with_wiring_section(self):
        """Parse wiring information."""
        content = """<!-- @lang:en -->

## Step 1: Setup Device {#device type=esp32_usb required=true}

Setup the device.

### Wiring

![Wiring Diagram](gallery/wiring.png)

1. Connect USB cable
2. Press boot button

<!-- @lang:zh -->

## 步骤 1: 设置设备 {#device type=esp32_usb required=true}

设置设备。

### 接线

![接线图](gallery/wiring.png)

1. 连接 USB 线
2. 按下启动按钮
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        step = result.steps[0]
        assert step.section.wiring is not None
        assert step.section.wiring.image == "gallery/wiring.png"
        assert len(step.section.wiring.steps.get("en")) == 2
        assert "Connect USB" in step.section.wiring.steps.get("en")[0]

    def test_preset_sections(self):
        """Parse preset groupings."""
        content = """<!-- @lang:en -->

# Overview

General overview.

## Preset: Cloud Solution {#cloud}

Cloud solution description.

## Step 1: Deploy Cloud {#cloud_deploy type=docker_deploy required=true}

Cloud step content.

## Preset: Edge Computing {#edge}

Edge solution description.

## Step 1: Deploy Edge {#edge_deploy type=script required=true}

Edge step content.

<!-- @lang:zh -->

# 概述

总体概述。

## 套餐: 云方案 {#cloud}

云方案描述。

## 步骤 1: 部署云服务 {#cloud_deploy type=docker_deploy required=true}

云步骤内容。

## 套餐: 边缘计算 {#edge}

边缘方案描述。

## 步骤 1: 部署边缘 {#edge_deploy type=script required=true}

边缘步骤内容。
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors
        assert len(result.presets) == 2

        cloud = result.presets[0]
        assert cloud.id == "cloud"
        assert cloud.name.get("en") == "Cloud Solution"
        assert cloud.name.get("zh") == "云方案"
        assert len(cloud.steps) == 1
        assert cloud.steps[0].id == "cloud_deploy"

        edge = result.presets[1]
        assert edge.id == "edge"
        assert len(edge.steps) == 1


class TestValidStepTypes:
    """Tests for valid step type validation."""

    def test_all_valid_types(self):
        """All documented step types are valid."""
        expected_types = {
            "docker_deploy",
            "docker_local",
            "docker_remote",
            "ssh_deb",
            "script",
            "manual",
            "esp32_usb",
            "himax_usb",
            "preview",
            "recamera_cpp",
            "recamera_nodered",
            "serial_camera",
            "ha_integration",
        }
        assert _get_valid_step_types() == expected_types

    @pytest.mark.parametrize("step_type", _get_valid_step_types())
    def test_each_valid_type_parses(self, step_type):
        """Each valid step type parses without error."""
        content = f"""<!-- @lang:en -->

## Step 1: Test {'{'}#test type={step_type} required=true{'}'}

Test content.
"""
        result = parse_deployment_guide(content)
        assert not result.has_errors, f"Type {step_type} should be valid"
