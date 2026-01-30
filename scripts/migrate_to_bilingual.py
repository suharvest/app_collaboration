#!/usr/bin/env python3
"""
Migration script to convert solution documents to the new bilingual format.

This script supports TWO modes:

1. MERGE mode (default): Converts separate EN/ZH files into merged bilingual format
   - intro/description.md + intro/description_zh.md → description.md (bilingual)
   - deploy/guide.md + deploy/guide_zh.md + sections/*.md → guide.md (bilingual)
   - intro/gallery/* → gallery/* (moved to root)

2. SPLIT mode (--split): Splits merged bilingual files into separate EN/ZH files
   - description.md (merged) → description.md (EN only) + description_zh.md (ZH only)
   - guide.md (merged) → guide.md (EN only) + guide_zh.md (ZH only)
   - Updates solution.yaml to reference both files

Usage:
    python scripts/migrate_to_bilingual.py [solution_id] [--dry-run] [--verbose] [--split]

Examples:
    # Preview split for smart_warehouse
    python scripts/migrate_to_bilingual.py smart_warehouse --split --dry-run

    # Split merged files for smart_warehouse
    python scripts/migrate_to_bilingual.py smart_warehouse --split

    # Split all solutions
    python scripts/migrate_to_bilingual.py --all --split

    # Merge mode (original behavior)
    python scripts/migrate_to_bilingual.py --all
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

import yaml


def read_file(path: Path) -> str:
    """Read file content, return empty string if not exists."""
    if path.exists():
        return path.read_text(encoding='utf-8')
    return ""


def merge_bilingual(en_content: str, zh_content: str) -> str:
    """Merge English and Chinese content into bilingual format."""
    result = []

    if en_content.strip():
        result.append("<!-- @lang:en -->")
        result.append("")
        result.append(en_content.strip())
        result.append("")

    if zh_content.strip():
        result.append("<!-- @lang:zh -->")
        result.append("")
        result.append(zh_content.strip())
        result.append("")

    return "\n".join(result)


def split_bilingual_file(merged_content: str) -> tuple:
    """Split merged bilingual content into separate EN and ZH content.

    Args:
        merged_content: Content with <!-- @lang:en --> and <!-- @lang:zh --> markers

    Returns:
        Tuple of (en_content, zh_content)
    """
    import re

    # Check if content has language markers
    if '<!-- @lang:' not in merged_content:
        # No markers, return as-is (assume it's EN only)
        return merged_content.strip(), ""

    # Find EN section
    en_match = re.search(
        r'<!--\s*@lang:en\s*-->\s*(.*?)(?=<!--\s*@lang:|$)',
        merged_content,
        re.DOTALL
    )
    en_content = en_match.group(1).strip() if en_match else ""

    # Find ZH section
    zh_match = re.search(
        r'<!--\s*@lang:zh\s*-->\s*(.*?)(?=<!--\s*@lang:|$)',
        merged_content,
        re.DOTALL
    )
    zh_content = zh_match.group(1).strip() if zh_match else ""

    return en_content, zh_content


def migrate_description(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Migrate intro/description.md and intro/description_zh.md to root description.md."""
    intro_dir = solution_path / "intro"

    en_file = intro_dir / "description.md"
    zh_file = intro_dir / "description_zh.md"
    target_file = solution_path / "description.md"

    en_content = read_file(en_file)
    zh_content = read_file(zh_file)

    if not en_content and not zh_content:
        print(f"  ⚠️  No description files found in {intro_dir}")
        return False

    merged = merge_bilingual(en_content, zh_content)

    if verbose:
        print(f"  📝 description.md preview ({len(merged)} chars):")
        preview = merged[:500] + "..." if len(merged) > 500 else merged
        for line in preview.split('\n')[:10]:
            print(f"      {line}")

    if dry_run:
        print(f"  [DRY-RUN] Would create: {target_file}")
        return True

    target_file.write_text(merged, encoding='utf-8')
    print(f"  ✅ Created: {target_file}")
    return True


def extract_step_id_from_yaml(device: dict) -> str:
    """Extract step ID from device definition."""
    return device.get('id', 'unknown')


def device_to_step_header(device: dict, step_num: int) -> str:
    """Convert device definition to step header format."""
    device_id = device.get('id', 'step')
    device_type = device.get('type', 'manual')
    required = device.get('required', True)
    config = device.get('config_file', '')

    # Build header
    header = f"## Step {step_num}: {device.get('name', device_id)}"
    attrs = [f"#{{#{device_id}", f"type={device_type}", f"required={'true' if required else 'false'}"]
    if config:
        attrs.append(f"config={config}")
    header += " {" + " ".join(attrs) + "}"

    return header


def format_step_content(device: dict, section_content: str, troubleshoot_content: str, wiring: dict) -> str:
    """Format step content with subsections."""
    lines = []

    # Main content
    if section_content.strip():
        lines.append(section_content.strip())
        lines.append("")

    # Wiring section
    if wiring:
        lines.append("### Wiring")
        lines.append("")
        if wiring.get('image'):
            # Note: image paths may need adjustment
            lines.append(f"![Wiring]({wiring['image']})")
            lines.append("")
        if wiring.get('steps'):
            for i, step in enumerate(wiring['steps'], 1):
                lines.append(f"{i}. {step}")
            lines.append("")

    # Troubleshooting section
    if troubleshoot_content.strip():
        lines.append("### Troubleshooting")
        lines.append("")
        lines.append(troubleshoot_content.strip())
        lines.append("")

    return "\n".join(lines)


def migrate_guide(solution_path: Path, yaml_data: dict, dry_run: bool = False, verbose: bool = False) -> bool:
    """Migrate deploy guide and sections to single guide.md."""
    deploy_dir = solution_path / "deploy"
    sections_dir = deploy_dir / "sections"

    # Read guide files
    guide_en = read_file(deploy_dir / "guide.md")
    guide_zh = read_file(deploy_dir / "guide_zh.md")

    # Read success files
    success_en = read_file(deploy_dir / "success.md")
    success_zh = read_file(deploy_dir / "success_zh.md")

    # For complex solutions with presets, we need to:
    # 1. Include preset sections
    # 2. Include device step sections
    # 3. Merge targets content

    # This is complex - for now, create a simple merged guide
    # The actual step content will be parsed from YAML references

    en_parts = []
    zh_parts = []

    # Add guide overview
    if guide_en.strip():
        en_parts.append(guide_en.strip())
        en_parts.append("")
    if guide_zh.strip():
        zh_parts.append(guide_zh.strip())
        zh_parts.append("")

    # Process presets if present
    presets = yaml_data.get('intro', {}).get('presets', [])
    for preset in presets:
        preset_id = preset.get('id', 'preset')
        preset_name = preset.get('name', preset_id)
        preset_name_zh = preset.get('name_zh', preset_name)

        # Add preset header
        en_parts.append(f"## Preset: {preset_name} {{#{preset_id}}}")
        en_parts.append("")
        zh_parts.append(f"## 套餐: {preset_name_zh} {{#{preset_id}}}")
        zh_parts.append("")

        # Add preset section content if present
        preset_section = preset.get('section', {})
        if preset_section.get('description_file'):
            en_content = read_file(solution_path / preset_section['description_file'])
            if en_content:
                en_parts.append(en_content.strip())
                en_parts.append("")
        if preset_section.get('description_file_zh'):
            zh_content = read_file(solution_path / preset_section['description_file_zh'])
            if zh_content:
                zh_parts.append(zh_content.strip())
                zh_parts.append("")

        # Process devices in preset
        devices = preset.get('devices', [])
        for idx, device in enumerate(devices, 1):
            device_id = device.get('id', 'device')
            device_name = device.get('name', device_id)
            device_name_zh = device.get('name_zh', device_name)
            device_type = device.get('type', 'manual')
            required = device.get('required', True)
            config = device.get('config_file', '')

            # Build step header
            attrs = f"type={device_type} required={'true' if required else 'false'}"
            if config:
                attrs += f" config={config}"

            en_parts.append(f"## Step {idx}: {device_name} {{#{device_id} {attrs}}}")
            en_parts.append("")
            zh_parts.append(f"## 步骤 {idx}: {device_name_zh} {{#{device_id} {attrs}}}")
            zh_parts.append("")

            # Add device section content
            device_section = device.get('section', {})
            if device_section.get('description_file'):
                content = read_file(solution_path / device_section['description_file'])
                if content:
                    en_parts.append(content.strip())
                    en_parts.append("")
            if device_section.get('description_file_zh'):
                content = read_file(solution_path / device_section['description_file_zh'])
                if content:
                    zh_parts.append(content.strip())
                    zh_parts.append("")

            # Add wiring if present
            wiring = device_section.get('wiring', {})
            if wiring:
                en_parts.append("### Wiring")
                en_parts.append("")
                zh_parts.append("### 接线")
                zh_parts.append("")

                if wiring.get('image'):
                    img_path = wiring['image']
                    en_parts.append(f"![Wiring]({img_path})")
                    en_parts.append("")
                    zh_parts.append(f"![接线图]({img_path})")
                    zh_parts.append("")

                if wiring.get('steps'):
                    for i, step in enumerate(wiring['steps'], 1):
                        en_parts.append(f"{i}. {step}")
                    en_parts.append("")
                if wiring.get('steps_zh'):
                    for i, step in enumerate(wiring['steps_zh'], 1):
                        zh_parts.append(f"{i}. {step}")
                    zh_parts.append("")

            # Add troubleshooting if present
            if device_section.get('troubleshoot_file'):
                content = read_file(solution_path / device_section['troubleshoot_file'])
                if content:
                    en_parts.append("### Troubleshooting")
                    en_parts.append("")
                    en_parts.append(content.strip())
                    en_parts.append("")
            if device_section.get('troubleshoot_file_zh'):
                content = read_file(solution_path / device_section['troubleshoot_file_zh'])
                if content:
                    zh_parts.append("### 故障排除")
                    zh_parts.append("")
                    zh_parts.append(content.strip())
                    zh_parts.append("")

            # Process targets if present
            targets = device.get('targets', {})
            for target_id, target in targets.items():
                target_name = target.get('name', target_id)
                target_name_zh = target.get('name_zh', target_name)
                target_config = target.get('config_file', '')
                is_default = target.get('default', False)

                # Add target header
                target_attrs = f"config={target_config}" if target_config else ""
                if is_default:
                    target_attrs += " default=true"

                en_parts.append(f"### Target: {target_name} {{#{device_id}_{target_id} {target_attrs}}}")
                en_parts.append("")
                zh_parts.append(f"### 部署目标: {target_name_zh} {{#{device_id}_{target_id} {target_attrs}}}")
                zh_parts.append("")

                # Add target section content
                target_section = target.get('section', {})
                if target_section.get('description_file'):
                    content = read_file(solution_path / target_section['description_file'])
                    if content:
                        en_parts.append(content.strip())
                        en_parts.append("")
                if target_section.get('description_file_zh'):
                    content = read_file(solution_path / target_section['description_file_zh'])
                    if content:
                        zh_parts.append(content.strip())
                        zh_parts.append("")

                # Add target wiring if present
                target_wiring = target_section.get('wiring', {})
                if target_wiring:
                    if target_wiring.get('image'):
                        en_parts.append(f"![Wiring]({target_wiring['image']})")
                        en_parts.append("")
                        zh_parts.append(f"![接线图]({target_wiring['image']})")
                        zh_parts.append("")

                    if target_wiring.get('steps'):
                        for i, step in enumerate(target_wiring['steps'], 1):
                            en_parts.append(f"{i}. {step}")
                        en_parts.append("")
                    if target_wiring.get('steps_zh'):
                        for i, step in enumerate(target_wiring['steps_zh'], 1):
                            zh_parts.append(f"{i}. {step}")
                        zh_parts.append("")

                # Add target troubleshooting
                if target_section.get('troubleshoot_file'):
                    content = read_file(solution_path / target_section['troubleshoot_file'])
                    if content:
                        en_parts.append("#### Troubleshooting")
                        en_parts.append("")
                        en_parts.append(content.strip())
                        en_parts.append("")
                if target_section.get('troubleshoot_file_zh'):
                    content = read_file(solution_path / target_section['troubleshoot_file_zh'])
                    if content:
                        zh_parts.append("#### 故障排除")
                        zh_parts.append("")
                        zh_parts.append(content.strip())
                        zh_parts.append("")

            en_parts.append("---")
            en_parts.append("")
            zh_parts.append("---")
            zh_parts.append("")

    # Add success section
    if success_en.strip():
        en_parts.append("# Deployment Complete")
        en_parts.append("")
        en_parts.append(success_en.strip())
        en_parts.append("")

    if success_zh.strip():
        zh_parts.append("# 部署完成")
        zh_parts.append("")
        zh_parts.append(success_zh.strip())
        zh_parts.append("")

    # Merge bilingual content
    merged = merge_bilingual("\n".join(en_parts), "\n".join(zh_parts))

    target_file = solution_path / "guide.md"

    if verbose:
        print(f"  📝 guide.md preview ({len(merged)} chars):")
        preview = merged[:1000] + "..." if len(merged) > 1000 else merged
        for line in preview.split('\n')[:20]:
            print(f"      {line}")

    if dry_run:
        print(f"  [DRY-RUN] Would create: {target_file}")
        return True

    target_file.write_text(merged, encoding='utf-8')
    print(f"  ✅ Created: {target_file}")
    return True


def migrate_gallery(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Move intro/gallery/* to root gallery/."""
    intro_gallery = solution_path / "intro" / "gallery"
    target_gallery = solution_path / "gallery"

    if not intro_gallery.exists():
        print(f"  ⚠️  No gallery folder found in {intro_gallery}")
        return False

    files = list(intro_gallery.iterdir())
    if not files:
        print(f"  ⚠️  Gallery folder is empty")
        return False

    if verbose:
        print(f"  📁 Moving {len(files)} files from intro/gallery to gallery/")

    if dry_run:
        print(f"  [DRY-RUN] Would move {len(files)} files to: {target_gallery}")
        return True

    target_gallery.mkdir(exist_ok=True)
    for f in files:
        target = target_gallery / f.name
        if f.is_file():
            shutil.copy2(f, target)
            if verbose:
                print(f"    📄 Copied: {f.name}")

    print(f"  ✅ Moved gallery ({len(files)} files)")
    return True


def update_yaml(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Update solution.yaml to use new file paths."""
    yaml_path = solution_path / "solution.yaml"

    if not yaml_path.exists():
        print(f"  ❌ solution.yaml not found")
        return False

    content = yaml_path.read_text(encoding='utf-8')
    data = yaml.safe_load(content)

    # Update intro fields
    intro = data.get('intro', {})

    # Update description paths
    if 'description_file' in intro:
        intro['description_file'] = 'description.md'
    if 'description_file_zh' in intro:
        del intro['description_file_zh']  # Remove, now bilingual

    # Update gallery paths
    if 'cover_image' in intro and intro['cover_image'].startswith('intro/gallery/'):
        intro['cover_image'] = intro['cover_image'].replace('intro/gallery/', 'gallery/')

    if 'gallery' in intro:
        for item in intro['gallery']:
            if item.get('src', '').startswith('intro/gallery/'):
                item['src'] = item['src'].replace('intro/gallery/', 'gallery/')

    # Update deployment guide path
    deployment = data.get('deployment', {})
    if 'guide_file' in deployment:
        deployment['guide_file'] = 'guide.md'
    if 'guide_file_zh' in deployment:
        del deployment['guide_file_zh']  # Remove, now bilingual

    # Remove post_deployment file references
    post_dep = deployment.get('post_deployment', {})
    if 'success_message_file' in post_dep:
        del post_dep['success_message_file']
    if 'success_message_file_zh' in post_dep:
        del post_dep['success_message_file_zh']

    # Note: preset section files will be removed in a subsequent step
    # For now, just mark them for manual review

    if verbose:
        print("  📝 Updated YAML structure")

    if dry_run:
        print(f"  [DRY-RUN] Would update: {yaml_path}")
        return True

    # Write updated YAML
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"  ✅ Updated: {yaml_path}")
    return True


def cleanup_old_files(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Remove old file structure after migration."""
    files_to_remove = []

    intro_dir = solution_path / "intro"
    if (intro_dir / "description.md").exists():
        files_to_remove.append(intro_dir / "description.md")
    if (intro_dir / "description_zh.md").exists():
        files_to_remove.append(intro_dir / "description_zh.md")

    deploy_dir = solution_path / "deploy"
    sections_dir = deploy_dir / "sections"

    # Old deploy files
    for f in ["guide.md", "guide_zh.md", "success.md", "success_zh.md"]:
        if (deploy_dir / f).exists():
            files_to_remove.append(deploy_dir / f)

    # All section files
    if sections_dir.exists():
        for f in sections_dir.iterdir():
            if f.suffix == '.md':
                files_to_remove.append(f)

    if verbose:
        print(f"  🗑️  Files to remove: {len(files_to_remove)}")
        for f in files_to_remove[:10]:
            print(f"      {f.relative_to(solution_path)}")
        if len(files_to_remove) > 10:
            print(f"      ... and {len(files_to_remove) - 10} more")

    if dry_run:
        print(f"  [DRY-RUN] Would remove {len(files_to_remove)} files")
        return True

    for f in files_to_remove:
        f.unlink()

    # Remove empty directories
    if sections_dir.exists() and not any(sections_dir.iterdir()):
        sections_dir.rmdir()

    print(f"  ✅ Cleaned up {len(files_to_remove)} old files")
    return True


def split_description(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Split merged description.md into description.md (EN) and description_zh.md (ZH)."""
    merged_file = solution_path / "description.md"

    if not merged_file.exists():
        print(f"  ⚠️  No description.md found to split")
        return False

    content = read_file(merged_file)

    # Check if file has language markers (is merged format)
    if '<!-- @lang:' not in content:
        print(f"  ⚠️  description.md is not in merged format, skipping")
        return True

    en_content, zh_content = split_bilingual_file(content)

    if verbose:
        print(f"  📝 EN content: {len(en_content)} chars")
        print(f"  📝 ZH content: {len(zh_content)} chars")

    if dry_run:
        print(f"  [DRY-RUN] Would split description.md → EN ({len(en_content)} chars) + ZH ({len(zh_content)} chars)")
        return True

    # Write EN content
    if en_content:
        (solution_path / "description.md").write_text(en_content + "\n", encoding='utf-8')
        print(f"  ✅ Wrote: description.md (EN, {len(en_content)} chars)")

    # Write ZH content
    if zh_content:
        (solution_path / "description_zh.md").write_text(zh_content + "\n", encoding='utf-8')
        print(f"  ✅ Wrote: description_zh.md (ZH, {len(zh_content)} chars)")

    return True


def split_guide(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Split merged guide.md into guide.md (EN) and guide_zh.md (ZH)."""
    merged_file = solution_path / "guide.md"

    if not merged_file.exists():
        print(f"  ⚠️  No guide.md found to split")
        return False

    content = read_file(merged_file)

    # Check if file has language markers (is merged format)
    if '<!-- @lang:' not in content:
        print(f"  ⚠️  guide.md is not in merged format, skipping")
        return True

    en_content, zh_content = split_bilingual_file(content)

    if verbose:
        print(f"  📝 EN content: {len(en_content)} chars")
        print(f"  📝 ZH content: {len(zh_content)} chars")

    if dry_run:
        print(f"  [DRY-RUN] Would split guide.md → EN ({len(en_content)} chars) + ZH ({len(zh_content)} chars)")
        return True

    # Write EN content
    if en_content:
        (solution_path / "guide.md").write_text(en_content + "\n", encoding='utf-8')
        print(f"  ✅ Wrote: guide.md (EN, {len(en_content)} chars)")

    # Write ZH content
    if zh_content:
        (solution_path / "guide_zh.md").write_text(zh_content + "\n", encoding='utf-8')
        print(f"  ✅ Wrote: guide_zh.md (ZH, {len(zh_content)} chars)")

    return True


def update_yaml_for_split(solution_path: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Update solution.yaml to reference separate EN and ZH files."""
    yaml_path = solution_path / "solution.yaml"

    if not yaml_path.exists():
        print(f"  ❌ solution.yaml not found")
        return False

    content = yaml_path.read_text(encoding='utf-8')
    data = yaml.safe_load(content)

    # Update intro section
    intro = data.get('intro', {})

    # Add description_file_zh if description_zh.md exists
    if (solution_path / "description_zh.md").exists() or not dry_run:
        intro['description_file'] = 'description.md'
        intro['description_file_zh'] = 'description_zh.md'

    # Update deployment section
    deployment = data.get('deployment', {})

    # Add guide_file_zh if guide_zh.md exists
    if (solution_path / "guide_zh.md").exists() or not dry_run:
        deployment['guide_file'] = 'guide.md'
        deployment['guide_file_zh'] = 'guide_zh.md'

    if verbose:
        print(f"  📝 Updated YAML with separate file references")

    if dry_run:
        print(f"  [DRY-RUN] Would update: {yaml_path}")
        return True

    # Write updated YAML
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"  ✅ Updated: {yaml_path}")
    return True


def split_solution(solution_id: str, solutions_dir: Path, dry_run: bool = False, verbose: bool = False) -> bool:
    """Split merged bilingual files in a solution into separate EN and ZH files."""
    solution_path = solutions_dir / solution_id

    if not solution_path.exists():
        print(f"❌ Solution not found: {solution_id}")
        return False

    yaml_path = solution_path / "solution.yaml"
    if not yaml_path.exists():
        print(f"❌ No solution.yaml in: {solution_id}")
        return False

    print(f"\n📦 Splitting: {solution_id}")
    print(f"   Path: {solution_path}")

    success = True

    # Step 1: Split description
    print("\n  Step 1: Splitting description.md...")
    if not split_description(solution_path, dry_run, verbose):
        success = False

    # Step 2: Split guide
    print("\n  Step 2: Splitting guide.md...")
    if not split_guide(solution_path, dry_run, verbose):
        success = False

    # Step 3: Update YAML
    print("\n  Step 3: Updating solution.yaml...")
    if not update_yaml_for_split(solution_path, dry_run, verbose):
        success = False

    if success:
        print(f"\n✅ Split {'preview' if dry_run else 'complete'}: {solution_id}")
    else:
        print(f"\n⚠️  Split {'preview had issues' if dry_run else 'completed with issues'}: {solution_id}")

    return success


def migrate_solution(solution_id: str, solutions_dir: Path, dry_run: bool = False, verbose: bool = False, cleanup: bool = False) -> bool:
    """Migrate a single solution to the new bilingual format."""
    solution_path = solutions_dir / solution_id

    if not solution_path.exists():
        print(f"❌ Solution not found: {solution_id}")
        return False

    yaml_path = solution_path / "solution.yaml"
    if not yaml_path.exists():
        print(f"❌ No solution.yaml in: {solution_id}")
        return False

    print(f"\n📦 Migrating: {solution_id}")
    print(f"   Path: {solution_path}")

    # Load YAML for guide migration
    yaml_data = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))

    success = True

    # Step 1: Migrate description
    print("\n  Step 1: Migrating description...")
    if not migrate_description(solution_path, dry_run, verbose):
        success = False

    # Step 2: Migrate guide
    print("\n  Step 2: Migrating guide...")
    if not migrate_guide(solution_path, yaml_data, dry_run, verbose):
        success = False

    # Step 3: Move gallery
    print("\n  Step 3: Moving gallery...")
    if not migrate_gallery(solution_path, dry_run, verbose):
        pass  # Not critical

    # Step 4: Update YAML
    print("\n  Step 4: Updating solution.yaml...")
    if not update_yaml(solution_path, dry_run, verbose):
        success = False

    # Step 5: Cleanup (optional)
    if cleanup and not dry_run:
        print("\n  Step 5: Cleaning up old files...")
        cleanup_old_files(solution_path, dry_run, verbose)
    elif not dry_run:
        print("\n  Step 5: Skipping cleanup (run with --cleanup to remove old files)")

    if success:
        print(f"\n✅ Migration {'preview' if dry_run else 'complete'}: {solution_id}")
    else:
        print(f"\n⚠️  Migration {'preview had issues' if dry_run else 'completed with issues'}: {solution_id}")

    return success


def main():
    parser = argparse.ArgumentParser(description='Migrate solutions to bilingual format')
    parser.add_argument('solution_id', nargs='?', help='Solution ID to migrate/split')
    parser.add_argument('--all', action='store_true', help='Process all solutions')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without writing')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--cleanup', action='store_true', help='Remove old files after migration')
    parser.add_argument('--split', action='store_true', help='Split merged bilingual files into separate EN/ZH files')

    args = parser.parse_args()

    # Determine solutions directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    solutions_dir = project_root / "solutions"

    if not solutions_dir.exists():
        print(f"❌ Solutions directory not found: {solutions_dir}")
        sys.exit(1)

    # Choose operation based on --split flag
    if args.split:
        operation = split_solution
        operation_name = "split"
    else:
        operation = migrate_solution
        operation_name = "migrate"

    if args.all:
        # Process all solutions
        solutions = [d.name for d in solutions_dir.iterdir() if d.is_dir() and (d / "solution.yaml").exists()]
        print(f"Found {len(solutions)} solutions to {operation_name}")

        for sol_id in sorted(solutions):
            if args.split:
                split_solution(sol_id, solutions_dir, args.dry_run, args.verbose)
            else:
                migrate_solution(sol_id, solutions_dir, args.dry_run, args.verbose, args.cleanup)
    elif args.solution_id:
        # Process single solution
        if args.split:
            split_solution(args.solution_id, solutions_dir, args.dry_run, args.verbose)
        else:
            migrate_solution(args.solution_id, solutions_dir, args.dry_run, args.verbose, args.cleanup)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
