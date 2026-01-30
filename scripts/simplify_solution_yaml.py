#!/usr/bin/env python3
"""
Simplify solution.yaml files by removing redundant deployment data.

After the bilingual markdown simplification, all deployment information
is now parsed from guide.md. This script removes the obsolete fields
from solution.yaml files.

Fields to KEEP:
- version, id, name, name_zh (basic metadata)
- intro.summary, intro.summary_zh
- intro.description_file, intro.description_file_zh
- intro.cover_image
- intro.gallery
- intro.category
- intro.tags
- intro.stats
- intro.links
- intro.partners (optional)
- intro.presets (only id, name, name_zh, badge, badge_zh, description, description_zh)
- deployment.guide_file, deployment.guide_file_zh
- deployment.selection_mode

Fields to REMOVE:
- intro.device_catalog
- intro.presets[].device_groups
- intro.presets[].architecture_image
- intro.presets[].links
- intro.presets[].section
- intro.presets[].devices
- deployment.devices
- deployment.order
- deployment.post_deployment
"""

import yaml
from pathlib import Path


def simplify_preset(preset: dict) -> dict:
    """Keep only essential preset fields for intro page."""
    return {
        "id": preset.get("id"),
        "name": preset.get("name"),
        "name_zh": preset.get("name_zh"),
        "badge": preset.get("badge"),
        "badge_zh": preset.get("badge_zh"),
        "description": preset.get("description"),
        "description_zh": preset.get("description_zh"),
    }


def simplify_solution_yaml(data: dict) -> dict:
    """Simplify solution.yaml data by removing redundant fields."""
    result = {
        "version": data.get("version", "1.0"),
        "id": data.get("id"),
        "name": data.get("name"),
        "name_zh": data.get("name_zh"),
    }

    # Simplify intro section
    if "intro" in data:
        intro = data["intro"]
        result["intro"] = {
            "summary": intro.get("summary"),
            "summary_zh": intro.get("summary_zh"),
            "description_file": intro.get("description_file", "description.md"),
            "description_file_zh": intro.get("description_file_zh", "description_zh.md"),
            "cover_image": intro.get("cover_image"),
            "gallery": intro.get("gallery", []),
            "category": intro.get("category"),
            "tags": intro.get("tags", []),
            "stats": intro.get("stats", {
                "difficulty": "beginner",
                "estimated_time": "30min",
                "deployed_count": 0,
                "likes_count": 0,
            }),
            "links": intro.get("links", {}),
        }

        # Simplify presets (keep only basic info for intro page display)
        if "presets" in intro:
            result["intro"]["presets"] = [
                simplify_preset(p) for p in intro["presets"]
            ]

        # Keep partners if present
        if "partners" in intro:
            result["intro"]["partners"] = intro["partners"]

    # Simplify deployment section
    if "deployment" in data:
        deploy = data["deployment"]
        result["deployment"] = {
            "guide_file": deploy.get("guide_file", "guide.md"),
            "guide_file_zh": deploy.get("guide_file_zh", "guide_zh.md"),
            "selection_mode": deploy.get("selection_mode", "sequential"),
        }

    return result


def clean_none_values(data):
    """Recursively remove None values from dict."""
    if isinstance(data, dict):
        return {k: clean_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [clean_none_values(item) for item in data]
    return data


def process_solution(solution_dir: Path) -> bool:
    """Process a single solution directory."""
    yaml_path = solution_dir / "solution.yaml"
    if not yaml_path.exists():
        return False

    print(f"Processing: {solution_dir.name}")

    # Read current YAML
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Get original size
    original_size = yaml_path.stat().st_size

    # Simplify
    simplified = simplify_solution_yaml(data)
    simplified = clean_none_values(simplified)

    # Write back
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(
            simplified,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=120,
        )

    # Get new size
    new_size = yaml_path.stat().st_size
    reduction = ((original_size - new_size) / original_size) * 100

    print(f"  {original_size} -> {new_size} bytes ({reduction:.1f}% reduction)")
    return True


def main():
    solutions_dir = Path(__file__).parent.parent / "solutions"

    if not solutions_dir.exists():
        print(f"Solutions directory not found: {solutions_dir}")
        return

    processed = 0
    for solution_path in sorted(solutions_dir.iterdir()):
        if solution_path.is_dir() and not solution_path.name.startswith("."):
            if process_solution(solution_path):
                processed += 1

    print(f"\nProcessed {processed} solutions")


if __name__ == "__main__":
    main()
