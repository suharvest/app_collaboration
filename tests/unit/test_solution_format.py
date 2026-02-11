"""
Validate all solutions follow the expected guide.md format conventions.

These tests scan real solution files to catch structural issues
that would cause rendering problems in the frontend.
"""

import re
from pathlib import Path

import pytest

from provisioning_station.services.markdown_parser import (
    parse_deployment_guide,
    validate_structure_consistency,
)

SOLUTIONS_DIR = Path(__file__).parent.parent.parent / "solutions"

# Patterns that indicate rich markdown content in target descriptions
RICH_CONTENT_PATTERNS = [
    (r"^\|.+\|", "table row"),
    (r"^\*\*[^*]+\*\*[:：]", "bold heading"),
    (r"^```", "code block"),
    (r"^[-*] ", "unordered list"),
    (r"^\d+\.\s+\*\*", "numbered list with bold"),
]

# Target header pattern (matches both EN and ZH)
TARGET_HEADER_RE = re.compile(
    r"^###\s+(?:Target|部署目标):\s+.+\{#(\w+)", re.MULTILINE
)

# Any H3 subsection header (### Wiring, ### Troubleshooting, etc.)
H3_HEADER_RE = re.compile(r"^###\s+", re.MULTILINE)


def get_solution_ids():
    """Get all solution IDs that have guide.md files."""
    if not SOLUTIONS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in SOLUTIONS_DIR.iterdir()
        if d.is_dir() and (d / "guide.md").exists()
    )


def get_guide_files():
    """Get all guide.md and guide_zh.md files as test parameters."""
    params = []
    for sol_id in get_solution_ids():
        sol_dir = SOLUTIONS_DIR / sol_id
        for guide_file in ["guide.md", "guide_zh.md"]:
            path = sol_dir / guide_file
            if path.exists():
                params.append(
                    pytest.param(sol_id, guide_file, id=f"{sol_id}/{guide_file}")
                )
    return params


def extract_target_descriptions(content: str) -> list[dict]:
    """Extract raw text between target headers and next H3 subsection.

    Returns list of {target_id, description_lines, line_number}.
    """
    lines = content.split("\n")
    targets = []
    current_target = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for target header
        target_match = TARGET_HEADER_RE.match(stripped)
        if target_match:
            # Save previous target
            if current_target:
                targets.append(current_target)
            current_target = {
                "target_id": target_match.group(1),
                "description_lines": [],
                "line_number": i,
            }
            continue

        # Check for any H3 header (ends current target description)
        if current_target and H3_HEADER_RE.match(stripped):
            targets.append(current_target)
            current_target = None
            continue

        # Check for H2 header or separator (ends current target)
        if current_target and (stripped.startswith("## ") or stripped == "---"):
            targets.append(current_target)
            current_target = None
            continue

        # Accumulate description lines
        if current_target and stripped:
            current_target["description_lines"].append(stripped)

    # Save last target
    if current_target:
        targets.append(current_target)

    return targets


# ============================================
# Test: Target descriptions should be brief
# ============================================


class TestTargetDescriptionFormat:
    """Target selector cards only show raw text, so descriptions must be brief.

    Rich markdown content (tables, lists, bold headings, code blocks) must
    go inside ### Wiring / ### 接线 subsections, not directly under the
    target header.
    """

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_target_description_no_rich_content(self, sol_id, guide_file):
        """Target description should not contain tables, lists, or other rich markdown."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        targets = extract_target_descriptions(content)

        violations = []
        for target in targets:
            for line in target["description_lines"]:
                for pattern, desc in RICH_CONTENT_PATTERNS:
                    if re.match(pattern, line):
                        violations.append(
                            f"  Target #{target['target_id']} (line {target['line_number']}): "
                            f"found {desc} in description: {line[:80]}"
                        )
                        break  # one violation per line is enough

        if violations:
            msg = (
                f"{sol_id}/{guide_file}: Target description contains rich markdown "
                f"that should be in ### Wiring / ### 接线 subsection:\n"
                + "\n".join(violations)
            )
            pytest.fail(msg)

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_target_description_not_too_long(self, sol_id, guide_file):
        """Target description should be brief (≤3 non-empty lines)."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        targets = extract_target_descriptions(content)

        MAX_LINES = 3
        violations = []
        for target in targets:
            n = len(target["description_lines"])
            if n > MAX_LINES:
                preview = " | ".join(target["description_lines"][:3])
                violations.append(
                    f"  Target #{target['target_id']} (line {target['line_number']}): "
                    f"{n} lines (max {MAX_LINES}): {preview[:100]}..."
                )

        if violations:
            msg = (
                f"{sol_id}/{guide_file}: Target description too long. "
                f"Move detailed content to ### Wiring / ### 接线 subsection:\n"
                + "\n".join(violations)
            )
            pytest.fail(msg)


# ============================================
# Test: Bilingual structure consistency
# ============================================


class TestBilingualConsistency:
    """EN and ZH guide files must have matching structure."""

    @pytest.mark.parametrize(
        "sol_id",
        [
            pytest.param(sid, id=sid)
            for sid in get_solution_ids()
            if (SOLUTIONS_DIR / sid / "guide_zh.md").exists()
        ],
    )
    def test_en_zh_structure_matches(self, sol_id):
        """guide.md and guide_zh.md should have matching preset/step/target IDs."""
        en_content = (SOLUTIONS_DIR / sol_id / "guide.md").read_text(encoding="utf-8")
        zh_content = (SOLUTIONS_DIR / sol_id / "guide_zh.md").read_text(
            encoding="utf-8"
        )

        en_result = parse_deployment_guide(en_content)
        zh_result = parse_deployment_guide(zh_content)

        validation = validate_structure_consistency(en_result, zh_result)
        if not validation.valid:
            errors = "\n".join(f"  - {e}" for e in validation.errors)
            pytest.fail(f"{sol_id}: EN/ZH structure mismatch:\n{errors}")


# ============================================
# Test: Parse errors
# ============================================


class TestNoParseErrors:
    """All solution guide files should parse without errors."""

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_no_parse_errors(self, sol_id, guide_file):
        """Guide file should parse without errors."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        result = parse_deployment_guide(content)

        if result.has_errors:
            errors = "\n".join(f"  - {e}" for e in result.errors)
            pytest.fail(f"{sol_id}/{guide_file}: Parse errors:\n{errors}")


# ============================================
# Test: Required subsections
# ============================================


class TestRequiredSubsections:
    """Every deployable step should have a troubleshooting subsection."""

    # Types that don't need troubleshooting
    EXEMPT_TYPES = {"preview", "serial_camera"}

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_steps_have_troubleshooting(self, sol_id, guide_file):
        """Each non-manual step should have a troubleshooting section."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        result = parse_deployment_guide(content)

        missing = []
        all_steps = list(result.steps)
        for preset in result.presets:
            all_steps.extend(preset.steps)

        for step in all_steps:
            if step.type in self.EXEMPT_TYPES:
                continue

            # Check step-level troubleshoot
            has_troubleshoot = bool(
                step.section.troubleshoot.get("en")
                or step.section.troubleshoot.get("zh")
            )

            # For steps with targets, check target-level troubleshoot
            if step.targets:
                for target in step.targets:
                    if target.troubleshoot.get("en") or target.troubleshoot.get("zh"):
                        has_troubleshoot = True
                        break

            if not has_troubleshoot:
                missing.append(f"  Step #{step.id} (type={step.type})")

        if missing:
            pytest.fail(
                f"{sol_id}/{guide_file}: Steps missing troubleshooting section:\n"
                + "\n".join(missing)
            )
