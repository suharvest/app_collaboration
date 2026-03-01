#!/usr/bin/env python3
"""
Upload solution binary assets to Alibaba Cloud OSS and replace local YAML
paths with public URLs.

Usage:
    uv run python scripts/upload_assets_to_cloud.py --dry-run -v
    uv run python scripts/upload_assets_to_cloud.py --solution recamera_ecosystem -v
    uv run python scripts/upload_assets_to_cloud.py --skip-upload -v
"""

import argparse
import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OSS_BUCKET = "oss://sensecraft-statics/solution-app"
PUBLIC_URL_PREFIX = "https://sensecraft-statics.seeed.cc/solution-app"

UPLOAD_EXTENSIONS = {
    ".bin",
    ".img",
    ".tflite",
    ".cvimodel",
    ".deb",
    ".hef",
    ".mp4",
    ".mov",
}

# Regex to find config= attributes in guide.md headers
STEP_CONFIG_RE = re.compile(
    r"^##\s+(?:Step|步骤)\s+\d+.*config=([^\s}]+)", re.MULTILINE
)
TARGET_CONFIG_RE = re.compile(
    r"^###\s+(?:Target|部署目标):.+config=([^\s}]+)", re.MULTILINE
)

SOLUTIONS_DIR = Path(__file__).parent.parent / "solutions"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AssetRef:
    """A reference to a local binary asset found in a device YAML."""

    yaml_path: Path  # Absolute path to the YAML file
    dotted_path: str  # e.g. "firmware.source.path"
    local_path: Path  # Absolute path to the local file
    oss_key: str  # OSS object key
    url: str  # Public URL after upload
    sha256: str = ""  # Computed after upload/read
    checksum_path: Optional[str] = None  # Dotted path for checksum field


@dataclass
class MigrationPlan:
    """Collected plan for one solution."""

    solution_id: str
    assets: list[AssetRef] = field(default_factory=list)
    skipped_urls: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (yaml, dotted_path, url)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def should_upload(path: Path, dotted_path: str) -> bool:
    """Decide whether a file should be uploaded based on extension and context."""
    ext = path.suffix.lower()
    if ext in UPLOAD_EXTENSIONS:
        return True
    # binary.models[].path: .txt files are model dictionaries, upload them
    if ext == ".txt" and "binary.models" in dotted_path:
        return True
    return False


def find_config_yamls(solution_dir: Path) -> list[str]:
    """Parse guide.md files to find all config= YAML references."""
    configs: set[str] = set()
    for guide_name in ["guide.md", "guide_zh.md"]:
        guide_path = solution_dir / guide_name
        if not guide_path.exists():
            continue
        content = guide_path.read_text(encoding="utf-8")
        for pattern in (STEP_CONFIG_RE, TARGET_CONFIG_RE):
            for match in pattern.finditer(content):
                configs.add(match.group(1))
    return sorted(configs)


# ---------------------------------------------------------------------------
# YAML asset extraction
# ---------------------------------------------------------------------------


def _walk_yaml(data: dict, yaml_path: Path, solution_dir: Path) -> list[AssetRef]:
    """Extract all uploadable asset references from a parsed device YAML."""
    solution_id = solution_dir.name
    refs: list[AssetRef] = []

    def _make_ref(
        dotted: str,
        raw_value: str,
        base_dir: Path,
        checksum_path: Optional[str] = None,
    ) -> Optional[AssetRef]:
        if not raw_value or is_url(raw_value):
            return None
        local = (base_dir / raw_value).resolve()
        if not should_upload(local, dotted):
            return None
        rel = local.relative_to(solution_dir.resolve())
        oss_key = f"{solution_id}/{rel.as_posix()}"
        url = f"{PUBLIC_URL_PREFIX}/{oss_key}"
        return AssetRef(
            yaml_path=yaml_path,
            dotted_path=dotted,
            local_path=local,
            oss_key=oss_key,
            url=url,
            checksum_path=checksum_path,
        )

    base_path = solution_dir

    # firmware.source.path
    firmware = data.get("firmware")
    if firmware:
        source = firmware.get("source")
        if source and source.get("path"):
            ref = _make_ref(
                "firmware.source.path",
                source["path"],
                base_path,
                "firmware.source.checksum",
            )
            if ref:
                refs.append(ref)

        flash_config = firmware.get("flash_config")
        if flash_config:
            # firmware.flash_config.partitions[i].file
            firmware_source_parent = ""
            if source and source.get("path") and not is_url(source["path"]):
                firmware_source_parent = str(
                    Path(source["path"]).parent
                )

            for i, part in enumerate(flash_config.get("partitions", [])):
                raw_file = part.get("file", "")
                if not raw_file or is_url(raw_file):
                    continue
                # Partition file is a bare filename; resolve via firmware source dir
                if firmware_source_parent:
                    full_rel = f"{firmware_source_parent}/{raw_file}"
                    local = (base_path / full_rel).resolve()
                else:
                    local = (base_path / raw_file).resolve()
                    full_rel = raw_file

                if not should_upload(local, f"firmware.flash_config.partitions[{i}].file"):
                    continue

                rel = local.relative_to(solution_dir.resolve())
                oss_key = f"{solution_id}/{rel.as_posix()}"
                url = f"{PUBLIC_URL_PREFIX}/{oss_key}"
                refs.append(
                    AssetRef(
                        yaml_path=yaml_path,
                        dotted_path=f"firmware.flash_config.partitions[{i}].file",
                        local_path=local,
                        oss_key=oss_key,
                        url=url,
                    )
                )

            # firmware.flash_config.models[i].path
            for i, model in enumerate(flash_config.get("models", [])):
                raw = model.get("path", "")
                ref = _make_ref(
                    f"firmware.flash_config.models[{i}].path",
                    raw,
                    base_path,
                    f"firmware.flash_config.models[{i}].checksum",
                )
                if ref:
                    refs.append(ref)

    # binary.deb_package.path and binary.models[i].path
    binary = data.get("binary")
    if binary:
        deb = binary.get("deb_package")
        if deb and deb.get("path"):
            ref = _make_ref(
                "binary.deb_package.path",
                deb["path"],
                base_path,
                "binary.deb_package.checksum",
            )
            if ref:
                refs.append(ref)

        for i, model in enumerate(binary.get("models", [])):
            raw = model.get("path", "")
            ref = _make_ref(
                f"binary.models[{i}].path",
                raw,
                base_path,
                f"binary.models[{i}].checksum",
            )
            if ref:
                refs.append(ref)

    # package.source.path
    package = data.get("package")
    if package:
        source = package.get("source")
        if source and source.get("path"):
            ref = _make_ref(
                "package.source.path",
                source["path"],
                base_path,
                "package.source.checksum",
            )
            if ref:
                refs.append(ref)

    return refs


def scan_solution(solution_dir: Path) -> MigrationPlan:
    """Scan one solution directory and build a migration plan."""
    solution_id = solution_dir.name
    plan = MigrationPlan(solution_id=solution_id)

    config_rels = find_config_yamls(solution_dir)
    if not config_rels:
        plan.warnings.append("No config= references found in guide.md")
        return plan

    yaml = YAML()
    yaml.preserve_quotes = True

    for config_rel in config_rels:
        yaml_path = solution_dir / config_rel
        if not yaml_path.exists():
            plan.warnings.append(f"Config file not found: {config_rel}")
            continue

        data = yaml.load(yaml_path.read_text(encoding="utf-8"))
        if not data:
            plan.warnings.append(f"Empty YAML: {config_rel}")
            continue

        refs = _walk_yaml(data, yaml_path, solution_dir)

        for ref in refs:
            if not ref.local_path.exists():
                # LFS pointer or missing file
                size = ref.local_path.stat().st_size if ref.local_path.exists() else 0
                plan.warnings.append(
                    f"File not found or LFS pointer: {ref.local_path} "
                    f"(referenced by {config_rel}:{ref.dotted_path})"
                )
                continue
            # Check if it's an LFS pointer (< 200 bytes, starts with "version https://git-lfs")
            if ref.local_path.stat().st_size < 200:
                try:
                    content = ref.local_path.read_text(encoding="utf-8", errors="ignore")
                    if content.startswith("version https://git-lfs"):
                        plan.warnings.append(
                            f"LFS pointer (not pulled): {ref.local_path.name} "
                            f"(run 'git lfs pull' first)"
                        )
                        continue
                except Exception:
                    pass

            plan.assets.append(ref)

    # Deduplicate by local_path (same file referenced from multiple YAMLs)
    # Keep all refs but mark duplicates so we only upload once
    return plan


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def upload_to_oss(asset: AssetRef, dry_run: bool = False) -> bool:
    """Upload a file to OSS using ossutil. Returns True on success."""
    oss_path = f"{OSS_BUCKET}/{asset.oss_key}"

    if dry_run:
        logger.info("  [DRY-RUN] Would upload: %s → %s", asset.local_path.name, oss_path)
        return True

    logger.info("  Uploading: %s → %s", asset.local_path.name, oss_path)
    try:
        result = subprocess.run(
            ["ossutil", "cp", str(asset.local_path), oss_path, "-f"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error("  ossutil failed: %s", result.stderr.strip())
            return False
        return True
    except FileNotFoundError:
        logger.error("  ossutil not found. Install: https://help.aliyun.com/document_detail/120075.html")
        return False
    except subprocess.TimeoutExpired:
        logger.error("  ossutil timed out for %s", asset.local_path.name)
        return False


# ---------------------------------------------------------------------------
# YAML modification
# ---------------------------------------------------------------------------


def _set_nested(data: dict, dotted_path: str, value):
    """Set a value in a nested dict using a dotted path with array indices."""
    parts = _parse_path(dotted_path)
    current = data
    for part, idx in parts[:-1]:
        current = current[part]
        if idx is not None:
            current = current[idx]
    last_part, last_idx = parts[-1]
    if last_idx is not None:
        current[last_part][last_idx] = value
    else:
        current[last_part] = value


def _get_nested(data: dict, dotted_path: str):
    """Get a value from a nested dict using a dotted path with array indices."""
    parts = _parse_path(dotted_path)
    current = data
    for part, idx in parts:
        current = current.get(part) if isinstance(current, dict) else None
        if current is None:
            return None
        if idx is not None:
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                return None
    return current


def _parse_path(dotted: str) -> list[tuple[str, Optional[int]]]:
    """Parse 'a.b[2].c' into [('a', None), ('b', 2), ('c', None)]."""
    result = []
    for segment in dotted.split("."):
        match = re.match(r"^(\w+)\[(\d+)\]$", segment)
        if match:
            result.append((match.group(1), int(match.group(2))))
        else:
            result.append((segment, None))
    return result


def _ensure_checksum(data: dict, checksum_path: str, sha256: str):
    """Ensure the checksum dict exists at the given path and set sha256."""
    parts = _parse_path(checksum_path)
    current = data
    for part, idx in parts[:-1]:
        current = current[part]
        if idx is not None:
            current = current[idx]

    last_part, last_idx = parts[-1]
    if last_idx is not None:
        container = current[last_part][last_idx]
    else:
        container = current

    if last_idx is not None:
        # The checksum is a key on container
        if not isinstance(container.get(last_part), dict) or container.get(last_part) is None:
            container[last_part] = {}
        container[last_part]["sha256"] = sha256
    else:
        if not isinstance(current.get(last_part), dict) or current.get(last_part) is None:
            current[last_part] = {}
        current[last_part]["sha256"] = sha256


def modify_yaml(yaml_path: Path, replacements: list[AssetRef], dry_run: bool = False):
    """Replace local paths with URLs in a YAML file, preserving formatting."""
    if not replacements:
        return

    yaml = YAML()
    yaml.preserve_quotes = True

    content = yaml_path.read_text(encoding="utf-8")
    data = yaml.load(content)

    for asset in replacements:
        # Replace path with URL
        _set_nested(data, asset.dotted_path, asset.url)
        logger.info(
            "  %s: %s → %s",
            yaml_path.name,
            asset.dotted_path,
            asset.url.split("/")[-1],
        )

        # Write checksum
        if asset.checksum_path and asset.sha256:
            _ensure_checksum(data, asset.checksum_path, asset.sha256)
            logger.debug("  Set checksum at %s", asset.checksum_path)

    if dry_run:
        logger.info("  [DRY-RUN] Would modify: %s", yaml_path.name)
        return

    # Backup original
    backup = yaml_path.with_suffix(".yaml.bak")
    shutil.copy2(yaml_path, backup)
    logger.debug("  Backup: %s", backup.name)

    # Write to temp file then atomic replace
    fd, tmp_path = tempfile.mkstemp(
        suffix=".yaml", dir=yaml_path.parent, prefix=".tmp_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        os.replace(tmp_path, yaml_path)
    except Exception:
        os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def get_solution_ids(specific: Optional[str] = None) -> list[str]:
    """Return solution IDs to process."""
    if specific:
        sol_dir = SOLUTIONS_DIR / specific
        if not sol_dir.exists():
            logger.error("Solution not found: %s", specific)
            sys.exit(1)
        return [specific]
    return sorted(
        d.name
        for d in SOLUTIONS_DIR.iterdir()
        if d.is_dir() and (d / "guide.md").exists()
    )


def process_solution(
    solution_id: str,
    dry_run: bool = False,
    skip_upload: bool = False,
    verbose: bool = False,
) -> MigrationPlan:
    """Process one solution: scan → upload → modify YAML."""
    solution_dir = SOLUTIONS_DIR / solution_id
    logger.info("=" * 60)
    logger.info("Solution: %s", solution_id)
    logger.info("=" * 60)

    plan = scan_solution(solution_dir)

    for w in plan.warnings:
        logger.warning("  %s", w)

    if not plan.assets:
        logger.info("  No uploadable assets found.")
        return plan

    # Deduplicate uploads by local_path
    uploaded: dict[Path, str] = {}  # local_path → sha256

    for asset in plan.assets:
        logger.info(
            "  Found: %s → %s (%s)",
            asset.dotted_path,
            asset.local_path.name,
            f"{asset.local_path.stat().st_size / 1024:.0f}KB",
        )

    logger.info("  Total: %d assets to process", len(plan.assets))

    # Upload phase
    if not skip_upload:
        seen_keys: set[str] = set()
        for asset in plan.assets:
            if asset.oss_key in seen_keys:
                logger.debug("  Skipping duplicate upload: %s", asset.oss_key)
                continue
            seen_keys.add(asset.oss_key)

            success = upload_to_oss(asset, dry_run=dry_run)
            if not success:
                logger.error("  Upload failed for %s, skipping YAML modification", asset.local_path.name)
                return plan

    # Compute sha256 for all assets
    for asset in plan.assets:
        if asset.local_path in uploaded:
            asset.sha256 = uploaded[asset.local_path]
        else:
            asset.sha256 = sha256_file(asset.local_path)
            uploaded[asset.local_path] = asset.sha256

    # Group replacements by YAML file
    by_yaml: dict[Path, list[AssetRef]] = {}
    for asset in plan.assets:
        by_yaml.setdefault(asset.yaml_path, []).append(asset)

    # Modify YAMLs
    for yaml_path, replacements in by_yaml.items():
        modify_yaml(yaml_path, replacements, dry_run=dry_run)

    return plan


def main():
    parser = argparse.ArgumentParser(
        description="Upload solution binary assets to Alibaba Cloud OSS"
    )
    parser.add_argument(
        "--solution",
        metavar="ID",
        help="Only process the specified solution (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: don't upload or modify files",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip ossutil upload, only modify YAMLs (for already-uploaded assets)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run unit tests after modification",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    solution_ids = get_solution_ids(args.solution)
    logger.info("Processing %d solution(s): %s", len(solution_ids), ", ".join(solution_ids))

    total_assets = 0
    total_warnings = 0

    for sol_id in solution_ids:
        plan = process_solution(
            sol_id,
            dry_run=args.dry_run,
            skip_upload=args.skip_upload,
            verbose=args.verbose,
        )
        total_assets += len(plan.assets)
        total_warnings += len(plan.warnings)

    logger.info("")
    logger.info("=" * 60)
    logger.info(
        "Done. %d assets processed, %d warnings.",
        total_assets,
        total_warnings,
    )
    if args.dry_run:
        logger.info("(DRY-RUN mode — no files were modified)")

    if args.verify:
        logger.info("Running unit tests...")
        result = subprocess.run(
            ["uv", "run", "--group", "test", "pytest", "tests/unit/", "-v"],
            cwd=SOLUTIONS_DIR.parent,
        )
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
