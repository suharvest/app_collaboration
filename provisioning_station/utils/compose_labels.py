"""
Docker Compose label injection utility

Adds SenseCraft labels to compose files for tracking deployed applications.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
import tempfile
import shutil

logger = logging.getLogger(__name__)

# Label prefix for SenseCraft managed containers
LABEL_PREFIX = "sensecraft"

# Standard labels
LABELS = {
    "managed": f"{LABEL_PREFIX}.managed",
    "solution_id": f"{LABEL_PREFIX}.solution_id",
    "solution_name": f"{LABEL_PREFIX}.solution_name",
    "device_id": f"{LABEL_PREFIX}.device_id",
    "deployed_at": f"{LABEL_PREFIX}.deployed_at",
    "deployed_by": f"{LABEL_PREFIX}.deployed_by",
}


def create_labels(
    solution_id: str,
    device_id: str,
    solution_name: Optional[str] = None,
) -> Dict[str, str]:
    """Create standard SenseCraft labels for a deployment"""
    return {
        LABELS["managed"]: "true",
        LABELS["solution_id"]: solution_id,
        LABELS["solution_name"]: solution_name or solution_id,
        LABELS["device_id"]: device_id,
        LABELS["deployed_at"]: datetime.utcnow().isoformat(),
        LABELS["deployed_by"]: "sensecraft-provisioning",
    }


def inject_labels_to_compose(
    compose_content: str,
    labels: Dict[str, str],
) -> str:
    """
    Inject labels into all services in a compose file content.

    Args:
        compose_content: Original compose file content as string
        labels: Labels to inject into each service

    Returns:
        Modified compose file content with labels injected
    """
    try:
        compose_data = yaml.safe_load(compose_content)

        if not compose_data or "services" not in compose_data:
            logger.warning("No services found in compose file")
            return compose_content

        for service_name, service_config in compose_data.get("services", {}).items():
            if service_config is None:
                service_config = {}
                compose_data["services"][service_name] = service_config

            # Get existing labels or create empty dict
            existing_labels = service_config.get("labels", {})

            # Handle labels as list format (convert to dict)
            if isinstance(existing_labels, list):
                labels_dict = {}
                for label in existing_labels:
                    if "=" in label:
                        key, value = label.split("=", 1)
                        labels_dict[key] = value
                existing_labels = labels_dict

            # Merge with new labels (new labels take precedence)
            merged_labels = {**existing_labels, **labels}
            service_config["labels"] = merged_labels

            logger.debug(f"Injected labels into service: {service_name}")

        # Dump back to YAML, preserving order
        return yaml.dump(compose_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse compose file: {e}")
        return compose_content
    except Exception as e:
        logger.error(f"Failed to inject labels: {e}")
        return compose_content


def inject_labels_to_compose_file(
    compose_path: str,
    labels: Dict[str, str],
    output_path: Optional[str] = None,
) -> str:
    """
    Inject labels into a compose file and save to output path.

    Args:
        compose_path: Path to original compose file
        labels: Labels to inject
        output_path: Path to save modified file (defaults to temp file)

    Returns:
        Path to the modified compose file
    """
    try:
        with open(compose_path, "r") as f:
            original_content = f.read()

        modified_content = inject_labels_to_compose(original_content, labels)

        if output_path:
            with open(output_path, "w") as f:
                f.write(modified_content)
            return output_path
        else:
            # Create temp file in same directory to preserve relative paths
            compose_dir = Path(compose_path).parent
            temp_fd, temp_path = tempfile.mkstemp(
                suffix=".yml",
                prefix="compose_",
                dir=str(compose_dir)
            )
            with open(temp_path, "w") as f:
                f.write(modified_content)
            return temp_path

    except Exception as e:
        logger.error(f"Failed to process compose file: {e}")
        raise


def get_label_filter() -> str:
    """Get Docker filter string for SenseCraft managed containers"""
    return f"label={LABELS['managed']}=true"


def parse_container_labels(labels: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Parse SenseCraft labels from container labels.

    Args:
        labels: Container labels dict

    Returns:
        Parsed SenseCraft metadata or None if not a managed container
    """
    if labels.get(LABELS["managed"]) != "true":
        return None

    return {
        "solution_id": labels.get(LABELS["solution_id"]),
        "solution_name": labels.get(LABELS["solution_name"]),
        "device_id": labels.get(LABELS["device_id"]),
        "deployed_at": labels.get(LABELS["deployed_at"]),
        "deployed_by": labels.get(LABELS["deployed_by"]),
    }
