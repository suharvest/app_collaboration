"""
Unit tests for compose_labels utility functions
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from provisioning_station.utils.compose_labels import (
    LABEL_PREFIX,
    LABELS,
    create_labels,
    inject_labels_to_compose,
    inject_labels_to_compose_file,
    get_label_filter,
    parse_container_labels,
)


class TestCreateLabels:
    """Tests for create_labels function"""

    def test_creates_required_labels(self):
        """Test that all required labels are created"""
        labels = create_labels(
            solution_id="test_solution",
            device_id="device_1"
        )

        assert labels[LABELS["managed"]] == "true"
        assert labels[LABELS["solution_id"]] == "test_solution"
        assert labels[LABELS["device_id"]] == "device_1"
        assert LABELS["deployed_at"] in labels
        assert labels[LABELS["deployed_by"]] == "sensecraft-provisioning"

    def test_solution_name_defaults_to_id(self):
        """Test that solution_name defaults to solution_id"""
        labels = create_labels(
            solution_id="my_solution",
            device_id="dev1"
        )
        assert labels[LABELS["solution_name"]] == "my_solution"

    def test_custom_solution_name(self):
        """Test custom solution name"""
        labels = create_labels(
            solution_id="my_solution",
            device_id="dev1",
            solution_name="My Custom Solution"
        )
        assert labels[LABELS["solution_name"]] == "My Custom Solution"

    def test_deployed_at_is_iso_format(self):
        """Test that deployed_at is in ISO format"""
        labels = create_labels(
            solution_id="test",
            device_id="dev"
        )
        # Should be parseable as ISO datetime
        deployed_at = labels[LABELS["deployed_at"]]
        datetime.fromisoformat(deployed_at)  # Should not raise


class TestInjectLabelsToCompose:
    """Tests for inject_labels_to_compose function"""

    def test_injects_labels_to_all_services(self, sample_compose_content):
        """Test that labels are injected to all services"""
        labels = {"test.label": "value"}
        result = inject_labels_to_compose(sample_compose_content, labels)

        parsed = yaml.safe_load(result)
        assert "test.label" in parsed["services"]["webapp"]["labels"]
        assert "test.label" in parsed["services"]["database"]["labels"]

    def test_preserves_existing_labels_dict(self, sample_compose_with_labels):
        """Test that existing dict labels are preserved"""
        labels = {"new.label": "new_value"}
        result = inject_labels_to_compose(sample_compose_with_labels, labels)

        parsed = yaml.safe_load(result)
        webapp_labels = parsed["services"]["webapp"]["labels"]
        # Existing labels should be preserved (after conversion from list)
        assert "new.label" in webapp_labels

    def test_converts_list_labels_to_dict(self, sample_compose_labels_list):
        """Test that list-format labels are converted to dict"""
        labels = {"injected.label": "injected_value"}
        result = inject_labels_to_compose(sample_compose_labels_list, labels)

        parsed = yaml.safe_load(result)
        webapp_labels = parsed["services"]["webapp"]["labels"]
        # Should be a dict now
        assert isinstance(webapp_labels, dict)
        assert webapp_labels.get("existing.label") == "value"
        assert webapp_labels.get("another.label") == "value2"
        assert webapp_labels.get("injected.label") == "injected_value"

    def test_new_labels_override_existing(self):
        """Test that new labels override existing ones"""
        content = """version: '3.8'
services:
  app:
    image: nginx
    labels:
      override.me: old_value
"""
        labels = {"override.me": "new_value"}
        result = inject_labels_to_compose(content, labels)

        parsed = yaml.safe_load(result)
        assert parsed["services"]["app"]["labels"]["override.me"] == "new_value"

    def test_handles_service_with_no_labels(self):
        """Test adding labels to service with no existing labels"""
        content = """version: '3.8'
services:
  simple:
    image: alpine
"""
        labels = {"new.label": "value"}
        result = inject_labels_to_compose(content, labels)

        parsed = yaml.safe_load(result)
        assert parsed["services"]["simple"]["labels"]["new.label"] == "value"

    def test_handles_empty_compose(self):
        """Test handling of compose with no services"""
        content = """version: '3.8'
"""
        labels = {"test.label": "value"}
        result = inject_labels_to_compose(content, labels)

        # Should return original content unchanged
        assert result == content

    def test_handles_invalid_yaml(self):
        """Test handling of invalid YAML content"""
        content = "invalid: yaml: content: :"
        labels = {"test.label": "value"}
        result = inject_labels_to_compose(content, labels)

        # Should return original content unchanged
        assert result == content

    def test_handles_null_service_config(self):
        """Test handling of null service configuration"""
        content = """version: '3.8'
services:
  null_service:
"""
        labels = {"test.label": "value"}
        result = inject_labels_to_compose(content, labels)

        parsed = yaml.safe_load(result)
        # Should create labels for null service
        assert parsed["services"]["null_service"]["labels"]["test.label"] == "value"


class TestInjectLabelsToComposeFile:
    """Tests for inject_labels_to_compose_file function"""

    def test_creates_temp_file_by_default(self, sample_compose_content):
        """Test that temp file is created when no output path specified"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_path = Path(tmpdir) / "docker-compose.yml"
            compose_path.write_text(sample_compose_content)

            labels = {"test.label": "value"}
            result_path = inject_labels_to_compose_file(
                str(compose_path),
                labels
            )

            assert os.path.exists(result_path)
            assert result_path != str(compose_path)
            assert result_path.endswith(".yml")

            # Verify content
            with open(result_path) as f:
                parsed = yaml.safe_load(f)
            assert "test.label" in parsed["services"]["webapp"]["labels"]

            # Cleanup
            os.unlink(result_path)

    def test_writes_to_specified_output_path(self, sample_compose_content):
        """Test writing to specified output path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_path = Path(tmpdir) / "docker-compose.yml"
            output_path = Path(tmpdir) / "docker-compose.modified.yml"
            compose_path.write_text(sample_compose_content)

            labels = {"test.label": "value"}
            result_path = inject_labels_to_compose_file(
                str(compose_path),
                labels,
                output_path=str(output_path)
            )

            assert result_path == str(output_path)
            assert output_path.exists()

    def test_handles_utf8_content(self):
        """Test handling of UTF-8 content"""
        content = """version: '3.8'
services:
  app:
    image: nginx
    labels:
      chinese.label: 中文标签
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_path = Path(tmpdir) / "docker-compose.yml"
            compose_path.write_text(content, encoding="utf-8")

            labels = {"new.chinese": "新标签"}
            result_path = inject_labels_to_compose_file(
                str(compose_path),
                labels
            )

            with open(result_path, encoding="utf-8") as f:
                parsed = yaml.safe_load(f)

            assert parsed["services"]["app"]["labels"]["chinese.label"] == "中文标签"
            assert parsed["services"]["app"]["labels"]["new.chinese"] == "新标签"

            os.unlink(result_path)


class TestGetLabelFilter:
    """Tests for get_label_filter function"""

    def test_returns_correct_filter_string(self):
        """Test that correct Docker filter string is returned"""
        filter_str = get_label_filter()
        assert filter_str == f"label={LABELS['managed']}=true"
        assert "sensecraft.managed=true" in filter_str


class TestParseContainerLabels:
    """Tests for parse_container_labels function"""

    def test_parses_managed_container(self):
        """Test parsing labels from managed container"""
        labels = {
            LABELS["managed"]: "true",
            LABELS["solution_id"]: "test_solution",
            LABELS["solution_name"]: "Test Solution",
            LABELS["device_id"]: "device_1",
            LABELS["deployed_at"]: "2024-01-15T10:30:00",
            LABELS["deployed_by"]: "sensecraft-provisioning",
        }

        result = parse_container_labels(labels)

        assert result is not None
        assert result["solution_id"] == "test_solution"
        assert result["solution_name"] == "Test Solution"
        assert result["device_id"] == "device_1"
        assert result["deployed_at"] == "2024-01-15T10:30:00"

    def test_returns_none_for_unmanaged_container(self):
        """Test that None is returned for unmanaged containers"""
        labels = {
            "some.other.label": "value",
            "another.label": "value2"
        }

        result = parse_container_labels(labels)
        assert result is None

    def test_returns_none_for_managed_false(self):
        """Test that None is returned when managed is not 'true'"""
        labels = {
            LABELS["managed"]: "false",
            LABELS["solution_id"]: "test"
        }

        result = parse_container_labels(labels)
        assert result is None

    def test_handles_missing_optional_labels(self):
        """Test handling of missing optional labels"""
        labels = {
            LABELS["managed"]: "true",
            LABELS["solution_id"]: "test_solution"
            # Missing other labels
        }

        result = parse_container_labels(labels)

        assert result is not None
        assert result["solution_id"] == "test_solution"
        assert result["solution_name"] is None
        assert result["device_id"] is None


class TestLabelConstants:
    """Tests for label constants"""

    def test_label_prefix(self):
        """Test that label prefix is sensecraft"""
        assert LABEL_PREFIX == "sensecraft"

    def test_all_labels_use_prefix(self):
        """Test that all labels use the correct prefix"""
        for label_value in LABELS.values():
            assert label_value.startswith(LABEL_PREFIX)
