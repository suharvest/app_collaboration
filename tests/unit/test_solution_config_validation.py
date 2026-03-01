"""
On-demand solution config validation.

Verifies that each solution's device YAML configs:
- Parse into valid DeviceConfig models
- Reference registered deployer types
- Contain the domain-specific config sub-objects each deployer requires
- Generate correct deployment steps
- Reference asset files that actually exist on disk

Usage:
    # Validate all solutions
    uv run --group test pytest tests/unit/test_solution_config_validation.py -v

    # Validate a specific solution
    uv run --group test pytest tests/unit/test_solution_config_validation.py -v -k "smart_warehouse"

Not run in CI by default — intended for solution onboarding and auditing.
"""

import re
from pathlib import Path

import pytest
import yaml

from provisioning_station.deployers import DEPLOYER_REGISTRY
from provisioning_station.models.device import DeviceConfig
from provisioning_station.utils.step_registry import get_steps_for_config

pytestmark = pytest.mark.solution_validation

SOLUTIONS_DIR = Path(__file__).parent.parent.parent / "solutions"

# Step header regex: extracts config= attribute from guide.md step headers.
# Use [^\s}]+ to stop at whitespace or closing brace of {#...}.
STEP_CONFIG_RE = re.compile(
    r"^##\s+(?:Step|步骤)\s+\d+.*config=([^\s}]+)", re.MULTILINE
)
# Target header regex: extracts config= attribute from target headers
TARGET_CONFIG_RE = re.compile(
    r"^###\s+(?:Target|部署目标):.+config=([^\s}]+)", re.MULTILINE
)

# ============================================================
# Required domain config per deployer type.
#
# Each entry is a list of dotted paths that must be non-None
# on the loaded DeviceConfig.  An entry ending with "[]" means
# the attribute must be a non-empty list.
# ============================================================

REQUIRED_CONFIG: dict[str, list[str]] = {
    "esp32_usb": ["firmware", "firmware.flash_config"],
    "himax_usb": ["firmware", "firmware.flash_config", "firmware.source"],
    "docker_local": ["docker", "docker.compose_file"],
    "docker_remote": ["docker_remote", "docker_remote.compose_file"],
    "ssh_deb": ["ssh", "package"],
    "recamera_cpp": ["binary"],
    "recamera_nodered": ["nodered", "nodered.flow_file"],
    "script": ["script"],
    "manual": ["steps[]"],
    "ha_integration": ["ha_integration", "ha_integration.domain", "ha_integration.components_dir"],
    # These types have no strict config requirements:
    # preview, serial_camera
}


# ============================================================
# Helpers
# ============================================================


def _get_solution_ids() -> list[str]:
    """Return solution IDs that have at least one guide.md."""
    if not SOLUTIONS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in SOLUTIONS_DIR.iterdir()
        if d.is_dir() and (d / "guide.md").exists()
    )


def _collect_referenced_configs() -> list[tuple[str, str, Path]]:
    """Collect (solution_id, config_relative_path, yaml_path) for all
    device configs referenced from guide.md step/target headers."""
    items: list[tuple[str, str, Path]] = []
    seen: set[tuple[str, str]] = set()

    for sol_id in _get_solution_ids():
        sol_dir = SOLUTIONS_DIR / sol_id
        for guide_name in ["guide.md", "guide_zh.md"]:
            guide_path = sol_dir / guide_name
            if not guide_path.exists():
                continue
            content = guide_path.read_text(encoding="utf-8")
            for pattern in (STEP_CONFIG_RE, TARGET_CONFIG_RE):
                for match in pattern.finditer(content):
                    config_rel = match.group(1)
                    key = (sol_id, config_rel)
                    if key not in seen:
                        seen.add(key)
                        items.append(
                            (sol_id, config_rel, sol_dir / config_rel)
                        )
    return items


def _load_device_config(yaml_path: Path) -> DeviceConfig:
    """Load a device YAML and return a DeviceConfig, applying the same
    transforms as SolutionManager.load_device_config()."""
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    data["base_path"] = str(yaml_path.parent.parent)

    # Mirror SolutionManager: map deployment → script for script type
    if data.get("type") == "script" and "deployment" in data:
        data["script"] = data.pop("deployment")

    return DeviceConfig(**data)


def _resolve(obj, dotted_path: str):
    """Walk a dotted attribute path (e.g. 'firmware.flash_config')."""
    current = obj
    for part in dotted_path.split("."):
        if current is None:
            return None
        current = getattr(current, part, None)
    return current


# Build parametrize list from referenced configs
_REFERENCED = _collect_referenced_configs()
_PARAMS = [
    pytest.param(sol, rel, path, id=f"{sol}/{rel}")
    for sol, rel, path in _REFERENCED
]


# ============================================================
# Test A: Device config YAML is parseable
# ============================================================


class TestDeviceConfigParseable:
    """Each referenced device YAML must parse into a valid DeviceConfig."""

    @pytest.mark.parametrize("sol_id,config_rel,yaml_path", _PARAMS)
    def test_device_config_parseable(self, sol_id, config_rel, yaml_path):
        assert yaml_path.exists(), f"Config file missing: {yaml_path}"
        config = _load_device_config(yaml_path)
        assert config.id, f"DeviceConfig.id is empty in {yaml_path}"
        assert config.type, f"DeviceConfig.type is empty in {yaml_path}"


# ============================================================
# Test B: Deployer type is registered
# ============================================================


class TestDeployerTypeRegistered:
    """Each device config type must exist in the deployer registry."""

    @pytest.mark.parametrize("sol_id,config_rel,yaml_path", _PARAMS)
    def test_deployer_type_registered(self, sol_id, config_rel, yaml_path):
        config = _load_device_config(yaml_path)
        assert config.type in DEPLOYER_REGISTRY, (
            f"{sol_id}/{config_rel}: type '{config.type}' not in DEPLOYER_REGISTRY. "
            f"Registered types: {sorted(DEPLOYER_REGISTRY.keys())}"
        )


# ============================================================
# Test C: Required domain config present
# ============================================================


class TestRequiredDomainConfig:
    """Each deployer type requires certain config sub-objects."""

    @pytest.mark.parametrize("sol_id,config_rel,yaml_path", _PARAMS)
    def test_required_domain_config_present(self, sol_id, config_rel, yaml_path):
        config = _load_device_config(yaml_path)
        requirements = REQUIRED_CONFIG.get(config.type, [])
        if not requirements:
            return  # No requirements for this type

        missing = []
        for req in requirements:
            if req.endswith("[]"):
                # Must be a non-empty list
                attr = req[:-2]
                val = _resolve(config, attr)
                if not val:
                    missing.append(f"{attr} (must be non-empty list)")
            else:
                val = _resolve(config, req)
                if val is None:
                    missing.append(req)

        if missing:
            pytest.fail(
                f"{sol_id}/{config_rel} (type={config.type}): "
                f"missing required config: {', '.join(missing)}"
            )


# ============================================================
# Test D: Steps are generated correctly
# ============================================================


class TestStepsGenerated:
    """Device configs with a step-declaring deployer must produce steps."""

    @pytest.mark.parametrize("sol_id,config_rel,yaml_path", _PARAMS)
    def test_steps_generated(self, sol_id, config_rel, yaml_path):
        config = _load_device_config(yaml_path)
        deployer = DEPLOYER_REGISTRY.get(config.type)
        if not deployer:
            return  # Already caught by test B

        # If the deployer has step templates, we expect steps
        if not deployer.steps:
            # Deployer doesn't declare steps (e.g. preview, manual)
            # manual type must have YAML-declared steps
            if config.type == "manual" and not config.steps:
                pytest.fail(
                    f"{sol_id}/{config_rel}: manual type must declare steps in YAML"
                )
            return

        # Auto-generate steps if not in YAML
        if config.steps:
            steps = config.steps
        else:
            steps = get_steps_for_config(config)

        assert steps, (
            f"{sol_id}/{config_rel} (type={config.type}): "
            f"no deployment steps generated. Deployer expects steps: "
            f"{[s['id'] for s in deployer.steps]}"
        )

        # Verify step IDs are non-empty strings
        for step in steps:
            assert step.id, (
                f"{sol_id}/{config_rel}: step has empty id"
            )
            assert step.name, (
                f"{sol_id}/{config_rel}: step '{step.id}' has empty name"
            )


# ============================================================
# Test E: Referenced asset files exist
# ============================================================

# Maps (config_type) → list of (dotted_path, description)
# where dotted_path yields a file path relative to the solution base dir.
ASSET_CHECKS: dict[str, list[tuple[str, str]]] = {
    "esp32_usb": [
        ("firmware.source.path", "firmware binary"),
    ],
    "himax_usb": [
        ("firmware.source.path", "firmware binary"),
    ],
    "docker_local": [
        ("docker.compose_file", "docker-compose file"),
    ],
    "docker_remote": [
        ("docker_remote.compose_file", "docker-compose file"),
    ],
    "recamera_nodered": [
        ("nodered.flow_file", "Node-RED flow file"),
    ],
    "ha_integration": [
        ("ha_integration.components_dir", "HA custom components directory"),
    ],
}


def _collect_asset_paths(
    config: DeviceConfig, base_path: Path
) -> list[tuple[str, str, Path]]:
    """Collect (description, raw_relative, resolved_path) for all asset refs."""
    checks = ASSET_CHECKS.get(config.type, [])
    result: list[tuple[str, str, Path]] = []

    for dotted, desc in checks:
        val = _resolve(config, dotted)
        if val and isinstance(val, str):
            result.append((desc, val, base_path / val))

    # ESP32 partition files
    if config.type == "esp32_usb" and config.firmware and config.firmware.flash_config:
        firmware_dir = None
        firmware_rel = ""
        if config.firmware.source and config.firmware.source.path:
            src_path = config.firmware.source.path
            if not src_path.startswith(("http://", "https://")):
                firmware_rel = str(Path(src_path).parent)
                firmware_dir = (base_path / src_path).parent
        for part in config.firmware.flash_config.partitions:
            if part.file and part.file.startswith(("http://", "https://")):
                result.append((f"partition '{part.name}'", part.file, base_path / "dummy"))
            elif firmware_dir and part.file:
                rel = str(Path(firmware_rel) / part.file)
                result.append((f"partition '{part.name}'", rel, firmware_dir / part.file))

    # Himax model files
    if config.type == "himax_usb" and config.firmware and config.firmware.flash_config:
        for model in config.firmware.flash_config.models:
            if model.path:
                result.append((f"himax model '{model.id}'", model.path, base_path / model.path))

    # reCamera C++ deb package and model files
    if config.type == "recamera_cpp" and config.binary:
        if config.binary.deb_package and config.binary.deb_package.path:
            p = config.binary.deb_package.path
            result.append(("deb package", p, base_path / p))
        for model in config.binary.models:
            if model.path:
                result.append((f"model '{model.path}'", model.path, base_path / model.path))

    # Preview overlay scripts
    if config.type == "preview" and config.overlay:
        if config.overlay.script_file:
            result.append(("overlay script", config.overlay.script_file, base_path / config.overlay.script_file))
        for dep in config.overlay.dependencies:
            result.append(("overlay dependency", dep, base_path / dep))

    return result


class TestReferencedAssetsExist:
    """Asset files referenced in device configs must exist on disk."""

    @pytest.mark.parametrize("sol_id,config_rel,yaml_path", _PARAMS)
    def test_referenced_assets_exist(self, sol_id, config_rel, yaml_path):
        config = _load_device_config(yaml_path)
        base_path = Path(config.base_path) if config.base_path else yaml_path.parent.parent

        assets = _collect_asset_paths(config, base_path)
        if not assets:
            return  # No asset references to check

        missing = []
        for desc, raw_rel, path in assets:
            # Cloud assets (URLs) are not local files — skip existence check
            if raw_rel.startswith(("http://", "https://")):
                continue
            # Try base_path resolution first (how SolutionManager resolves)
            if path.resolve().exists():
                continue
            # Fallback: resolve relative to the YAML file's directory
            # (some configs use paths relative to devices/ subdirectory)
            alt = (yaml_path.parent / raw_rel).resolve()
            if alt.exists():
                continue
            missing.append(f"  {desc}: {raw_rel} (tried {path} and {alt})")

        if missing:
            pytest.fail(
                f"{sol_id}/{config_rel} (type={config.type}): "
                f"missing asset files:\n" + "\n".join(missing)
            )


# ============================================================
# Test F: Guide config= references are valid
# ============================================================


class TestGuideConfigReferencesValid:
    """Every config= path in guide.md step/target headers must point
    to an existing YAML file that can be parsed."""

    @pytest.mark.parametrize(
        "sol_id",
        [pytest.param(s, id=s) for s in _get_solution_ids()],
    )
    def test_guide_config_references_valid(self, sol_id):
        sol_dir = SOLUTIONS_DIR / sol_id
        missing_files: list[str] = []
        parse_errors: list[str] = []

        for guide_name in ["guide.md", "guide_zh.md"]:
            guide_path = sol_dir / guide_name
            if not guide_path.exists():
                continue

            content = guide_path.read_text(encoding="utf-8")
            config_paths: set[str] = set()
            for pattern in (STEP_CONFIG_RE, TARGET_CONFIG_RE):
                for match in pattern.finditer(content):
                    config_paths.add(match.group(1))

            for config_rel in sorted(config_paths):
                yaml_path = sol_dir / config_rel
                if not yaml_path.exists():
                    missing_files.append(
                        f"  {guide_name}: config={config_rel} -> file not found"
                    )
                    continue
                # Try parsing
                try:
                    _load_device_config(yaml_path)
                except Exception as e:
                    parse_errors.append(
                        f"  {guide_name}: config={config_rel} -> {type(e).__name__}"
                    )

        issues = missing_files + parse_errors
        if issues:
            pytest.fail(
                f"{sol_id}: guide.md config reference issues:\n"
                + "\n".join(issues)
            )
