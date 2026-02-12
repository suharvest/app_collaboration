"""
Verify auto-discovery registry matches the old hardcoded deployer set.

Tests cover:
- Registry contains all expected deployer types
- Every deployer has valid ui_traits with required keys
- Critical trait values match expected behavior
- Deployer steps match the legacy expected steps
"""


from provisioning_station.deployers import DEPLOYER_REGISTRY


def test_registry_contains_all_expected_types():
    """Registry has exactly the expected deployer types."""
    expected = {
        "esp32_usb", "himax_usb", "docker_local", "docker_remote",
        "ssh_deb", "script", "manual", "recamera_nodered",
        "recamera_cpp", "serial_camera", "ha_integration", "preview",
    }
    assert set(DEPLOYER_REGISTRY.keys()) == expected


def test_all_deployers_have_ui_traits():
    """Every deployer has valid ui_traits with required keys."""
    required_keys = {
        "connection", "auto_deploy", "renderer", "has_targets",
        "show_model_selection", "show_service_warning", "connection_scope",
    }
    for dtype, deployer in DEPLOYER_REGISTRY.items():
        assert hasattr(deployer, "ui_traits"), f"{dtype} missing ui_traits"
        for key in required_keys:
            assert key in deployer.ui_traits, f"{dtype} missing ui_traits.{key}"


def test_ui_traits_match_expected():
    """Spot-check critical trait values to prevent regressions."""
    # SSH types
    for t in ["ssh_deb", "docker_remote", "recamera_cpp", "recamera_nodered", "ha_integration"]:
        assert DEPLOYER_REGISTRY[t].ui_traits["connection"] == "ssh", f"{t} should be ssh"

    # Serial types
    for t in ["esp32_usb", "himax_usb"]:
        assert DEPLOYER_REGISTRY[t].ui_traits["connection"] == "serial", f"{t} should be serial"

    # Manual types
    assert DEPLOYER_REGISTRY["manual"].ui_traits["auto_deploy"] is False
    assert DEPLOYER_REGISTRY["preview"].ui_traits["renderer"] == "preview"
    assert DEPLOYER_REGISTRY["serial_camera"].ui_traits["renderer"] == "serial-camera"

    # Targets
    assert DEPLOYER_REGISTRY["recamera_cpp"].ui_traits["has_targets"] is True

    # Model selection
    assert DEPLOYER_REGISTRY["himax_usb"].ui_traits["show_model_selection"] is True

    # Service warning
    for t in ["recamera_cpp", "recamera_nodered"]:
        assert DEPLOYER_REGISTRY[t].ui_traits["show_service_warning"] is True


def test_deployer_steps_match_legacy():
    """Every deployer's steps match the old EXPECTED_BASE_STEPS from test_step_registry.py."""
    EXPECTED = {
        "docker_local": [
            "actions_before", "pull_images", "create_volumes",
            "start_services", "health_check", "actions_after",
        ],
        "docker_remote": [
            "connect", "check_os", "check_docker", "prepare",
            "actions_before", "upload", "pull_images",
            "start_services", "health_check", "actions_after",
        ],
        "esp32_usb": [
            "detect", "actions_before", "erase", "flash", "verify", "actions_after",
        ],
        "himax_usb": [
            "detect", "prepare", "actions_before", "flash", "verify", "actions_after",
        ],
        "recamera_cpp": [
            "connect", "precheck", "prepare", "transfer", "install",
            "models", "configure", "actions_after", "start", "verify",
        ],
        "recamera_nodered": [
            "prepare", "actions_before", "load_flow", "configure",
            "connect", "deploy", "verify", "actions_after",
        ],
        "script": [
            "validate", "actions_before", "setup", "configure",
            "start", "health_check", "actions_after",
        ],
        "preview": ["preview_setup"],
        "ha_integration": ["auth", "detect", "ssh", "copy", "restart", "integrate"],
    }
    for dtype, expected_ids in EXPECTED.items():
        deployer = DEPLOYER_REGISTRY.get(dtype)
        assert deployer is not None, f"Missing deployer for {dtype}"
        actual_ids = [s["id"] for s in deployer.steps]
        assert actual_ids == expected_ids, f"{dtype} steps mismatch: {actual_ids} != {expected_ids}"
