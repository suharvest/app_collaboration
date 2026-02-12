"""
Step registry for automatic deployment step generation.

Each deployer declares its own step templates as a class attribute.
This module reads those templates and generates ``DeploymentStep`` instances
based on device type and runtime conditions (actions_before / actions_after).

Conditional steps (marked with ``_condition``) are only included when
the condition is met in the device config.
"""

from typing import Dict, List

from ..deployers import DEPLOYER_REGISTRY
from ..models.device import DeploymentStep, DeviceConfig

# ---------------------------------------------------------------------------
# Backward-compatible computed dict (used by existing tests)
# ---------------------------------------------------------------------------

DEPLOYER_STEPS: Dict[str, List[dict]] = {
    dt: d.steps for dt, d in DEPLOYER_REGISTRY.items() if d.steps
}


def get_steps_for_config(config: DeviceConfig) -> List[DeploymentStep]:
    """Generate deployment steps from device type and actions config.

    Returns an empty list for types not in the registry (e.g. ``manual``),
    meaning the YAML must declare steps explicitly.
    """
    deployer = DEPLOYER_REGISTRY.get(config.type)
    if not deployer or not deployer.steps:
        return []

    steps: List[DeploymentStep] = []
    for entry in deployer.steps:
        condition = entry.get("_condition")
        if condition == "actions.before":
            if not (config.actions and config.actions.before):
                continue
        elif condition == "actions.after":
            if not (config.actions and config.actions.after):
                continue

        steps.append(
            DeploymentStep(
                id=entry["id"],
                name=entry["name"],
                name_zh=entry.get("name_zh"),
            )
        )

    return steps
