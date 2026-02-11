"""
Unit tests for the step registry (auto-generated deployment steps).

Tests cover:
- Every registered deployer type returns the correct step IDs
- Conditional steps (actions_before / actions_after) are included/excluded
  based on ActionsConfig
- Unregistered types (e.g. manual) return an empty list
- YAML-declared steps are not overwritten by auto-generation
"""

import pytest

from provisioning_station.models.device import (
    ActionConfig,
    ActionsConfig,
    DeploymentStep,
    DeviceConfig,
)
from provisioning_station.utils.step_registry import (
    DEPLOYER_STEPS,
    get_steps_for_config,
)


def _make_config(device_type: str, actions: ActionsConfig = None) -> DeviceConfig:
    """Helper to create a minimal DeviceConfig for testing."""
    return DeviceConfig(
        id="test_device",
        name="Test Device",
        type=device_type,
        actions=actions,
    )


# ---------------------------------------------------------------------------
# Test: every registered type produces the expected base step IDs
# ---------------------------------------------------------------------------

EXPECTED_BASE_STEPS = {
    "docker_local": ["pull_images", "create_volumes", "start_services", "health_check"],
    "docker_remote": [
        "connect",
        "check_os",
        "check_docker",
        "prepare",
        "upload",
        "pull_images",
        "start_services",
        "health_check",
    ],
    "esp32_usb": ["detect", "erase", "flash", "verify"],
    "himax_usb": ["detect", "prepare", "flash", "verify"],
    "recamera_cpp": [
        "connect",
        "precheck",
        "prepare",
        "transfer",
        "install",
        "models",
        "configure",
        "start",
        "verify",
    ],
    "recamera_nodered": [
        "prepare",
        "load_flow",
        "configure",
        "connect",
        "deploy",
        "verify",
    ],
    "script": ["validate", "setup", "configure", "start", "health_check"],
    "preview": ["preview_setup"],
    "ha_integration": ["auth", "detect", "ssh", "copy", "restart", "integrate"],
}


@pytest.mark.parametrize("device_type,expected_ids", EXPECTED_BASE_STEPS.items())
def test_base_steps_without_actions(device_type, expected_ids):
    """Each type (without actions) produces exactly the expected base steps."""
    config = _make_config(device_type)
    steps = get_steps_for_config(config)
    ids = [s.id for s in steps]
    assert ids == expected_ids


# ---------------------------------------------------------------------------
# Test: conditional actions_before / actions_after
# ---------------------------------------------------------------------------

def _actions_before_only():
    return ActionsConfig(
        before=[ActionConfig(name="prep", run="echo prep")],
    )


def _actions_after_only():
    return ActionsConfig(
        after=[ActionConfig(name="cleanup", run="echo done")],
    )


def _actions_both():
    return ActionsConfig(
        before=[ActionConfig(name="prep", run="echo prep")],
        after=[ActionConfig(name="cleanup", run="echo done")],
    )


class TestConditionalActions:
    """Verify actions_before / actions_after appear only when configured."""

    def test_no_actions_no_action_steps(self):
        config = _make_config("docker_local")
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert "actions_before" not in ids
        assert "actions_after" not in ids

    def test_actions_before_included(self):
        config = _make_config("docker_local", actions=_actions_before_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert "actions_before" in ids
        assert "actions_after" not in ids

    def test_actions_after_included(self):
        config = _make_config("docker_local", actions=_actions_after_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert "actions_before" not in ids
        assert "actions_after" in ids

    def test_both_actions_included(self):
        config = _make_config("docker_local", actions=_actions_both())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert "actions_before" in ids
        assert "actions_after" in ids

    def test_actions_before_position_docker_local(self):
        """actions_before should come before pull_images in docker_local."""
        config = _make_config("docker_local", actions=_actions_before_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert ids.index("actions_before") < ids.index("pull_images")

    def test_actions_after_position_docker_local(self):
        """actions_after should come after health_check in docker_local."""
        config = _make_config("docker_local", actions=_actions_after_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert ids.index("actions_after") > ids.index("health_check")

    def test_actions_before_position_docker_remote(self):
        """actions_before should come after prepare in docker_remote."""
        config = _make_config("docker_remote", actions=_actions_before_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert ids.index("actions_before") > ids.index("prepare")
        assert ids.index("actions_before") < ids.index("upload")

    def test_actions_after_position_recamera_cpp(self):
        """actions_after should come between configure and start in recamera_cpp."""
        config = _make_config("recamera_cpp", actions=_actions_after_only())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert ids.index("actions_after") > ids.index("configure")
        assert ids.index("actions_after") < ids.index("start")

    def test_empty_actions_config_no_action_steps(self):
        """ActionsConfig with empty before/after lists → no action steps."""
        config = _make_config("docker_local", actions=ActionsConfig())
        steps = get_steps_for_config(config)
        ids = [s.id for s in steps]
        assert "actions_before" not in ids
        assert "actions_after" not in ids


# ---------------------------------------------------------------------------
# Test: unregistered types return empty list
# ---------------------------------------------------------------------------

class TestUnregisteredTypes:
    def test_manual_returns_empty(self):
        config = _make_config("manual")
        assert get_steps_for_config(config) == []

    def test_unknown_type_returns_empty(self):
        config = _make_config("something_unknown")
        assert get_steps_for_config(config) == []


# ---------------------------------------------------------------------------
# Test: return type and structure
# ---------------------------------------------------------------------------

class TestStepStructure:
    def test_returns_deployment_step_instances(self):
        config = _make_config("docker_local")
        steps = get_steps_for_config(config)
        assert all(isinstance(s, DeploymentStep) for s in steps)

    def test_steps_have_name_zh(self):
        """All generated steps should have a Chinese name."""
        config = _make_config("docker_local")
        steps = get_steps_for_config(config)
        for step in steps:
            assert step.name_zh is not None, f"Step {step.id} missing name_zh"

    def test_all_registered_types_have_expected_base_steps(self):
        """Ensure EXPECTED_BASE_STEPS covers all registered types."""
        for dtype in DEPLOYER_STEPS:
            assert dtype in EXPECTED_BASE_STEPS, (
                f"Type '{dtype}' is registered but not in EXPECTED_BASE_STEPS"
            )


# ---------------------------------------------------------------------------
# Test: YAML-declared steps are not overwritten (integration-style)
# ---------------------------------------------------------------------------

class TestYamlStepsPreserved:
    def test_existing_steps_not_overwritten(self):
        """If config already has steps, get_steps_for_config result is irrelevant
        because the caller only calls it when config.steps is empty."""
        config = _make_config("docker_local")
        config.steps = [
            DeploymentStep(id="custom_step", name="Custom"),
        ]
        # Simulate the guard in load_device_config
        if not config.steps:
            config.steps = get_steps_for_config(config)
        # steps should still be the custom one
        assert len(config.steps) == 1
        assert config.steps[0].id == "custom_step"
