"""
Multilingual Markdown Parser for Solution Documentation.

This module provides parsing utilities for multilingual markdown format.
Supports both:
1. Combined format: Single file with `<!-- @lang:xx -->` markers
2. Separate format: Multiple files (guide.md, guide_zh.md, guide_ja.md, ...) with structure validation

Format specification:
- Deployment steps use H2 headers with metadata: `## Step N: Title {#step_id type=xxx required=true}`
- Preset sections: `## Preset: Name {#preset_id}` / `## 套餐: 名称 {#preset_id}`
- Sub-sections: `### Prerequisites`, `### Wiring`, `### Troubleshooting`
- Success section starts with `# Deployment Complete` / `# 部署完成`

Language file naming convention:
- guide.md       -> English (default)
- guide_zh.md    -> Chinese
- guide_ja.md    -> Japanese
- guide_fr.md    -> French
- etc.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import markdown

from .localized import Localized


class ParseErrorType(Enum):
    """Types of parsing errors."""

    NO_LANGUAGE_MARKERS = "no_language_markers"
    INVALID_STEP_FORMAT = "invalid_step_format"
    DUPLICATE_STEP_ID = "duplicate_step_id"
    INVALID_STEP_TYPE = "invalid_step_type"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_TARGET_FORMAT = "invalid_target_format"
    # Structure validation errors (for separate bilingual files)
    PRESET_COUNT_MISMATCH = "preset_count_mismatch"
    PRESET_ID_MISMATCH = "preset_id_mismatch"
    STEP_COUNT_MISMATCH = "step_count_mismatch"
    STEP_ID_MISMATCH = "step_id_mismatch"
    STEP_TYPE_MISMATCH = "step_type_mismatch"
    STEP_REQUIRED_MISMATCH = "step_required_mismatch"
    STEP_CONFIG_MISMATCH = "step_config_mismatch"


@dataclass
class ParseError:
    """Represents a parsing error with location and suggestion."""

    error_type: ParseErrorType
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        loc = f" (line {self.line_number})" if self.line_number else ""
        sug = f"\n  Suggestion: {self.suggestion}" if self.suggestion else ""
        return f"{self.message}{loc}{sug}"


@dataclass
class ParseWarning:
    """Represents a non-fatal parsing warning."""

    message: str
    line_number: Optional[int] = None


@dataclass
class WiringInfo:
    """Wiring diagram information extracted from markdown."""

    image: Optional[str] = None
    steps: Localized[list[str]] = field(default_factory=lambda: Localized())


@dataclass
class TargetInfo:
    """Target information for docker_deploy type devices."""

    id: str
    name: Localized[str] = field(default_factory=lambda: Localized())
    config_file: Optional[str] = None
    default: bool = False
    target_type: str = "local"  # "local" or "remote"
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # Plain text for selector
    description_html: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML for content area
    troubleshoot: Localized[str] = field(default_factory=lambda: Localized())  # HTML
    post_deploy: Localized[str] = field(default_factory=lambda: Localized())  # HTML
    wiring: Optional["WiringInfo"] = None


@dataclass
class SectionContent:
    """Section content compatible with existing frontend structure."""

    title: Localized[str] = field(default_factory=lambda: Localized())
    subtitle: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # Plain text extracted from first paragraph (for header subtitle)
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    troubleshoot: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    post_deploy: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    wiring: Optional[WiringInfo] = None


@dataclass
class DeploymentStep:
    """A parsed deployment step from the markdown."""

    id: str
    title: Localized[str] = field(default_factory=lambda: Localized())
    type: str = ""
    required: bool = True
    config_file: Optional[str] = None
    section: SectionContent = field(default_factory=SectionContent)
    targets: list[TargetInfo] = field(default_factory=list)


@dataclass
class PresetGuide:
    """A parsed preset guide section."""

    id: str
    name: Localized[str] = field(default_factory=lambda: Localized())
    description: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    steps: list[DeploymentStep] = field(default_factory=list)
    completion: Optional["SuccessContent"] = None
    is_default: bool = False


@dataclass
class SuccessContent:
    """Parsed success/completion content."""

    content: Localized[str] = field(default_factory=lambda: Localized())  # HTML content


@dataclass
class ParseResult:
    """Result of parsing a deployment guide markdown file."""

    overview: Localized[str] = field(
        default_factory=lambda: Localized()
    )  # HTML content
    presets: list[PresetGuide] = field(default_factory=list)
    steps: list[DeploymentStep] = field(
        default_factory=list
    )  # Steps without preset context
    success: Optional[SuccessContent] = None
    warnings: list[ParseWarning] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass
class StructureValidationResult:
    """Result of validating structure consistency between EN and ZH guide files."""

    valid: bool = True
    errors: list[ParseError] = field(default_factory=list)
    warnings: list[ParseWarning] = field(default_factory=list)
    en_presets: list[str] = field(default_factory=list)  # List of preset IDs in EN
    zh_presets: list[str] = field(default_factory=list)  # List of preset IDs in ZH
    en_steps_by_preset: dict = field(
        default_factory=dict
    )  # preset_id -> list of step IDs
    zh_steps_by_preset: dict = field(default_factory=dict)


# Valid deployment types
VALID_STEP_TYPES = {
    "docker_deploy",
    "docker_local",
    "docker_remote",
    "ssh_deb",
    "script",
    "manual",
    "esp32_usb",
    "himax_usb",
    "preview",
    "recamera_cpp",
    "recamera_nodered",
    "serial_camera",
    "ha_integration",
}

# Regex patterns
LANG_MARKER_PATTERN = re.compile(r"<!--\s*@lang:(\w+)\s*-->")
STEP_HEADER_PATTERN = re.compile(
    r"^##\s+(?:Step\s+\d+:\s*|步骤\s*\d+[：:]\s*)?(.+?)\s*\{#(\w+)([^}]*)\}\s*$",
    re.IGNORECASE,
)
PRESET_HEADER_PATTERN = re.compile(
    r"^##\s+Preset:\s*(.+?)\s*\{#(\w+)\}\s*$", re.IGNORECASE
)
PRESET_HEADER_ZH_PATTERN = re.compile(
    r"^##\s+套餐[：:]\s*(.+?)\s*\{#(\w+)\}\s*$", re.IGNORECASE
)
TARGET_HEADER_PATTERN = re.compile(
    r"^###\s+(?:Target|部署目标)[：:]?\s*(.+?)\s*\{#(\w+)([^}]*)\}\s*$", re.IGNORECASE
)
SUCCESS_HEADER_PATTERN = re.compile(
    r"^#\s+(Deployment\s+Complete|部署完成)\s*$", re.IGNORECASE
)
PRESET_COMPLETION_PATTERN = re.compile(
    r"^###\s+(Deployment\s+Complete|部署完成)\s*$", re.IGNORECASE
)
SUBSECTION_PATTERNS = {
    "prerequisites": re.compile(r"^###\s+(Prerequisites|前置条件)\s*$", re.IGNORECASE),
    "wiring": re.compile(r"^###\s+(Wiring|接线)\s*$", re.IGNORECASE),
    "troubleshoot": re.compile(
        r"^###\s+(Troubleshooting|故障排查|故障排除)\s*$", re.IGNORECASE
    ),
    "post_deploy": re.compile(
        r"^###\s+(Deployment\s+Complete|部署完成)\s*$", re.IGNORECASE
    ),
}
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
ORDERED_LIST_PATTERN = re.compile(r"^\d+\.\s+(.+)$")


def parse_step_attributes(attr_string: str) -> dict:
    """Parse step attributes from the header metadata string.

    Example: "type=docker_deploy required=true config=devices/docker.yaml"
    Returns: {"type": "docker_deploy", "required": True, "config": "devices/docker.yaml"}
    """
    attrs = {}
    # Match key=value pairs, where value can be quoted or unquoted
    pattern = re.compile(r'(\w+)=(?:"([^"]+)"|([^\s]+))')
    for match in pattern.finditer(attr_string):
        key = match.group(1)
        value = match.group(2) if match.group(2) else match.group(3)
        # Convert boolean strings
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        attrs[key] = value
    return attrs


def split_by_language(content: str) -> tuple[str, str]:
    """Split content by language markers.

    Returns (english_content, chinese_content).
    If no markers found, returns (content, "").
    """
    parts = LANG_MARKER_PATTERN.split(content)

    if len(parts) == 1:
        # No language markers found
        return content.strip(), ""

    english = ""
    chinese = ""

    i = 0
    while i < len(parts):
        if i + 1 < len(parts):
            lang = (
                parts[i].strip().lower() if parts[i].strip() in ("en", "zh") else None
            )
            if lang:
                text = parts[i + 1] if i + 1 < len(parts) else ""
                if lang == "en":
                    english = text.strip()
                elif lang == "zh":
                    chinese = text.strip()
                i += 2
                continue
        i += 1

    return english, chinese


def extract_wiring_for_lang(content: str) -> tuple[Optional[str], list[str]]:
    """Extract wiring image and steps from content for a single language.

    Args:
        content: Markdown content for one language

    Returns:
        Tuple of (image_path, steps_list)
    """
    image = None
    steps = []

    # Extract image
    img_match = IMAGE_PATTERN.search(content)
    if img_match:
        image = img_match.group(2)

    # Extract ordered list steps
    for line in content.split("\n"):
        match = ORDERED_LIST_PATTERN.match(line.strip())
        if match:
            steps.append(match.group(1))

    return image, steps


def extract_wiring(content: str, content_zh: str = "") -> Optional[WiringInfo]:
    """Extract wiring information from content (legacy bilingual interface).

    Args:
        content: English content
        content_zh: Chinese content (optional)

    Returns:
        WiringInfo with Localized steps, or None if no wiring content
    """
    image, steps_en = extract_wiring_for_lang(content)

    if not image and not steps_en:
        return None

    wiring = WiringInfo(image=image, steps=Localized({"en": steps_en}))

    # Extract Chinese steps if provided
    if content_zh:
        _, steps_zh = extract_wiring_for_lang(content_zh)
        if steps_zh:
            wiring.steps.set("zh", steps_zh)

    return wiring


def extract_wiring_multilang(lang_contents: Dict[str, str]) -> Optional[WiringInfo]:
    """Extract wiring information from multiple language contents.

    Args:
        lang_contents: Dict mapping language code to content

    Returns:
        WiringInfo with Localized steps for all languages
    """
    # Use first available content to get image
    image = None
    all_steps: Dict[str, list[str]] = {}

    for lang, content in lang_contents.items():
        lang_image, lang_steps = extract_wiring_for_lang(content)
        if lang_image and image is None:
            image = lang_image
        if lang_steps:
            all_steps[lang] = lang_steps

    if not image and not all_steps:
        return None

    return WiringInfo(image=image, steps=Localized(all_steps))


def md_to_html(content: str) -> str:
    """Convert markdown content to HTML."""
    if not content.strip():
        return ""
    return markdown.markdown(content, extensions=["tables", "fenced_code", "nl2br"])


def extract_subtitle(raw_markdown: str) -> str:
    """Extract the first paragraph of plain text from raw markdown.

    Scans lines, skipping blanks/images/headings/tables/lists, and returns
    the first line that is regular prose text with inline markdown stripped.
    Used as a short subtitle for deployment step headers.
    """
    for line in raw_markdown.strip().split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip images, headings, table rows, unordered lists, ordered lists
        if stripped.startswith(("![", "#", "|", "- ", "* ")) or re.match(
            r"^\d+\.", stripped
        ):
            continue
        # Strip inline markdown: [text](url) → text, **bold** → bold, `code` → code
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", stripped)
        text = re.sub(r"[*_`]+", "", text).strip()
        if text:
            return text
    return ""


def parse_subsections(content: str) -> dict[str, str]:
    """Parse subsections (Prerequisites, Wiring, Troubleshooting) from step content.

    Returns dict with keys: 'main', 'prerequisites', 'wiring', 'troubleshoot'
    """
    result = {
        "main": "",
        "prerequisites": "",
        "wiring": "",
        "troubleshoot": "",
        "post_deploy": "",
    }

    lines = content.split("\n")
    current_section = "main"
    section_content: dict[str, list[str]] = {k: [] for k in result}

    for line in lines:
        # Check for subsection headers
        found_section = False
        for section_name, pattern in SUBSECTION_PATTERNS.items():
            if pattern.match(line.strip()):
                current_section = section_name
                found_section = True
                break

        # Check for target header (don't include in subsections)
        if TARGET_HEADER_PATTERN.match(line.strip()):
            break

        if not found_section:
            section_content[current_section].append(line)

    for key, lines_list in section_content.items():
        result[key] = "\n".join(lines_list).strip()

    return result


def parse_deployment_step(
    header_line: str, content_en: str, content_zh: str, line_number: int
) -> tuple[Optional[DeploymentStep], list[ParseError], list[ParseWarning]]:
    """Parse a single deployment step from header and content (legacy bilingual).

    Returns (step, errors, warnings).
    """
    errors = []
    warnings = []

    # Parse header
    match = STEP_HEADER_PATTERN.match(header_line.strip())
    if not match:
        errors.append(
            ParseError(
                error_type=ParseErrorType.INVALID_STEP_FORMAT,
                message=f"Invalid step header format: {header_line}",
                line_number=line_number,
                suggestion="Use format: ## Step N: Title {#step_id type=xxx required=true}",
            )
        )
        return None, errors, warnings

    title = match.group(1).strip()
    step_id = match.group(2)
    attrs_str = match.group(3)
    attrs = parse_step_attributes(attrs_str)

    # Validate type
    step_type = attrs.get("type", "")
    if not step_type:
        errors.append(
            ParseError(
                error_type=ParseErrorType.MISSING_REQUIRED_FIELD,
                message=f"Step '{step_id}' missing required 'type' attribute",
                line_number=line_number,
                suggestion=f"Add type=xxx where xxx is one of: {', '.join(sorted(VALID_STEP_TYPES))}",
            )
        )
        return None, errors, warnings

    if step_type not in VALID_STEP_TYPES:
        errors.append(
            ParseError(
                error_type=ParseErrorType.INVALID_STEP_TYPE,
                message=f"Invalid step type '{step_type}' for step '{step_id}'",
                line_number=line_number,
                suggestion=f"Valid types: {', '.join(sorted(VALID_STEP_TYPES))}",
            )
        )
        return None, errors, warnings

    # Parse content subsections
    subsections_en = parse_subsections(content_en)
    subsections_zh = parse_subsections(content_zh)

    # Check for translation warning
    if not content_zh.strip():
        warnings.append(
            ParseWarning(
                message=f"Step '{step_id}' missing Chinese translation",
                line_number=line_number,
            )
        )

    # Build section content with Localized fields
    en_subtitle = extract_subtitle(subsections_en["main"])
    section = SectionContent(
        title=Localized({"en": title}),
        subtitle=Localized({"en": en_subtitle} if en_subtitle else {}),
        description=Localized(
            {
                "en": md_to_html(subsections_en["main"]),
            }
        ),
        troubleshoot=Localized(
            {
                "en": md_to_html(subsections_en.get("troubleshoot", "")),
            }
        ),
        post_deploy=Localized(
            {
                "en": md_to_html(subsections_en.get("post_deploy", "")),
            }
        ),
    )

    # Add Chinese content if available
    if subsections_zh.get("main"):
        section.description.set("zh", md_to_html(subsections_zh["main"]))
        zh_subtitle = extract_subtitle(subsections_zh["main"])
        if zh_subtitle:
            section.subtitle.set("zh", zh_subtitle)
    if subsections_zh.get("troubleshoot"):
        section.troubleshoot.set("zh", md_to_html(subsections_zh["troubleshoot"]))
    if subsections_zh.get("post_deploy"):
        section.post_deploy.set("zh", md_to_html(subsections_zh["post_deploy"]))

    # Extract wiring if present
    if subsections_en.get("wiring"):
        section.wiring = extract_wiring(
            subsections_en["wiring"], subsections_zh.get("wiring", "")
        )

    step = DeploymentStep(
        id=step_id,
        title=Localized({"en": title}),
        type=step_type,
        required=attrs.get("required", True),
        config_file=attrs.get("config"),
        section=section,
    )

    # Parse targets (for docker_deploy and recamera_cpp types)
    if step_type in ("docker_deploy", "recamera_cpp"):
        targets = parse_targets(content_en, content_zh)
        if targets:
            step.targets = targets

    return step, errors, warnings


def _parse_target_content(
    content_lines: list[str],
) -> tuple[str, list[str], Optional[str], str, str]:
    """Parse target content into description, wiring steps, wiring image, troubleshoot, and post_deploy.

    Returns: (description, wiring_steps, wiring_image, troubleshoot, post_deploy)
    """
    # Join lines and use parse_subsections for consistent parsing
    content = "\n".join(content_lines)

    # Truncate at separator or next target
    for i, line in enumerate(content_lines):
        stripped = line.strip()
        if stripped == "---" or TARGET_HEADER_PATTERN.match(stripped):
            content = "\n".join(content_lines[:i])
            break

    subsections = parse_subsections(content)

    # Extract wiring info
    wiring_steps = []
    wiring_image = None
    wiring_content = subsections.get("wiring", "")
    if wiring_content:
        for line in wiring_content.split("\n"):
            stripped = line.strip()
            # Extract image
            img_match = IMAGE_PATTERN.match(stripped)
            if img_match:
                wiring_image = img_match.group(2)
                continue
            # Extract ordered list steps
            list_match = ORDERED_LIST_PATTERN.match(stripped)
            if list_match:
                wiring_steps.append(list_match.group(1))

    # Main content is description
    description = subsections.get("main", "").strip()

    # Troubleshoot content (as markdown, will be converted to HTML later)
    troubleshoot = subsections.get("troubleshoot", "").strip()

    # Post-deploy content (as markdown, will be converted to HTML later)
    post_deploy = subsections.get("post_deploy", "").strip()

    return description, wiring_steps, wiring_image, troubleshoot, post_deploy


def _parse_targets_single_lang(content: str, lang: str) -> list[TargetInfo]:
    """Parse targets from single-language content.

    Args:
        content: Markdown content for one language
        lang: Language code

    Returns:
        List of TargetInfo with single-language Localized fields
    """
    targets = []
    lines = content.split("\n")
    current_target_id = None
    current_target_name = ""
    current_attrs = {}
    current_content: list[str] = []

    for line in lines:
        match = TARGET_HEADER_PATTERN.match(line.strip())
        if match:
            # Save previous target if exists
            if current_target_id:
                desc, wiring_steps, wiring_image, troubleshoot, post_deploy = (
                    _parse_target_content(current_content)
                )
                wiring = None
                if wiring_image or wiring_steps:
                    wiring = WiringInfo(
                        image=wiring_image,
                        steps=Localized({lang: wiring_steps}),
                    )
                target = TargetInfo(
                    id=current_target_id,
                    name=Localized({lang: current_target_name}),
                    config_file=current_attrs.get("config"),
                    default=current_attrs.get("default", False),
                    target_type=current_attrs.get("type", "local"),
                    description=Localized({lang: desc.strip() if desc else ""}),
                    description_html=Localized(
                        {lang: md_to_html(desc) if desc else ""}
                    ),
                    wiring=wiring,
                    troubleshoot=Localized(
                        {lang: md_to_html(troubleshoot) if troubleshoot else ""}
                    ),
                    post_deploy=Localized(
                        {lang: md_to_html(post_deploy) if post_deploy else ""}
                    ),
                )
                targets.append(target)

            # Start new target
            current_target_name = match.group(1).strip()
            current_target_id = match.group(2)
            current_attrs = parse_step_attributes(match.group(3))
            current_content = []
        else:
            if current_target_id:
                current_content.append(line)

    # Save last target
    if current_target_id:
        desc, wiring_steps, wiring_image, troubleshoot, post_deploy = (
            _parse_target_content(current_content)
        )
        wiring = None
        if wiring_image or wiring_steps:
            wiring = WiringInfo(
                image=wiring_image,
                steps=Localized({lang: wiring_steps}),
            )
        target = TargetInfo(
            id=current_target_id,
            name=Localized({lang: current_target_name}),
            config_file=current_attrs.get("config"),
            default=current_attrs.get("default", False),
            target_type=current_attrs.get("type", "local"),
            description=Localized({lang: desc.strip() if desc else ""}),
            description_html=Localized({lang: md_to_html(desc) if desc else ""}),
            wiring=wiring,
            troubleshoot=Localized(
                {lang: md_to_html(troubleshoot) if troubleshoot else ""}
            ),
            post_deploy=Localized(
                {lang: md_to_html(post_deploy) if post_deploy else ""}
            ),
        )
        targets.append(target)

    return targets


def parse_targets(content_en: str, content_zh: str) -> list[TargetInfo]:
    """Parse target sections from step content (legacy bilingual interface).

    Target format: ### Target: Name {#id config=xxx default=true}
    Content below each target header is the description + wiring steps.
    """
    # Parse English targets
    targets = _parse_targets_single_lang(content_en, "en")

    # Parse Chinese content and merge translations
    if content_zh and targets:
        zh_targets = _parse_targets_single_lang(content_zh, "zh")

        # Create a lookup by ID
        zh_by_id = {t.id: t for t in zh_targets}

        # Merge Chinese into English targets
        for target in targets:
            zh_target = zh_by_id.get(target.id)
            if zh_target:
                # Merge name
                target.name.set("zh", zh_target.name.get("zh"))
                # Merge description
                target.description.set("zh", zh_target.description.get("zh"))
                target.description_html.set("zh", zh_target.description_html.get("zh"))
                # Merge troubleshoot
                target.troubleshoot.set("zh", zh_target.troubleshoot.get("zh"))
                # Merge post_deploy
                target.post_deploy.set("zh", zh_target.post_deploy.get("zh"))
                # Merge wiring steps
                if target.wiring and zh_target.wiring:
                    target.wiring.steps.set("zh", zh_target.wiring.steps.get("zh"))

    return targets


def parse_deployment_guide(content: str) -> ParseResult:
    """Parse a complete deployment guide markdown file.

    The guide may contain:
    - Overview section at the top
    - Preset sections (## Preset: Name {#preset_id})
    - Step sections (## Step N: Title {#step_id type=xxx})
    - Success section (# Deployment Complete)

    Returns ParseResult with all parsed content.
    """
    result = ParseResult()

    # Split by language first
    content_en, content_zh = split_by_language(content)

    if not content_en and not content_zh:
        # Try treating entire content as English
        content_en = content

    # Check for language markers
    if not LANG_MARKER_PATTERN.search(content):
        result.warnings.append(
            ParseWarning(
                message="No language markers found. Using entire content as English."
            )
        )

    # Parse English content
    _parse_guide_content(content_en, "en", result)

    # Parse Chinese content to add translations
    if content_zh:
        _parse_guide_content(content_zh, "zh", result)

    return result


def _find_matching_step_in_zh(step_id: str, zh_steps: list[dict]) -> Optional[dict]:
    """Find matching step content in Chinese parsed content."""
    for s in zh_steps:
        if s.get("id") == step_id:
            return s
    return None


def _parse_guide_content(content: str, lang: str, result: ParseResult) -> None:
    """Parse guide content for a specific language and update result."""
    lines = content.split("\n")
    line_num = 0

    current_section = "overview"  # overview, preset, step, success
    current_preset: Optional[PresetGuide] = None
    current_step_header: Optional[str] = None
    current_step_content: list[str] = []
    current_step_line: int = 0
    seen_step_ids: set[str] = set()
    preset_description_lines: list[str] = []

    overview_lines: list[str] = []
    success_lines: list[str] = []

    def flush_step():
        """Process accumulated step content."""
        nonlocal current_step_header, current_step_content, current_step_line
        if current_step_header:
            content_text = "\n".join(current_step_content)
            if lang == "en":
                step, errors, warnings = parse_deployment_step(
                    current_step_header,
                    content_text,
                    "",  # zh content added later
                    current_step_line,
                )
                result.errors.extend(errors)
                result.warnings.extend(warnings)
                if step:
                    if step.id in seen_step_ids:
                        result.errors.append(
                            ParseError(
                                error_type=ParseErrorType.DUPLICATE_STEP_ID,
                                message=f"Duplicate step ID: {step.id}",
                                line_number=current_step_line,
                            )
                        )
                    else:
                        seen_step_ids.add(step.id)
                        if current_preset:
                            current_preset.steps.append(step)
                        else:
                            result.steps.append(step)
            else:
                # Update existing step with non-English content
                step_id_match = STEP_HEADER_PATTERN.match(current_step_header)
                if step_id_match:
                    step_id = step_id_match.group(2)
                    # Find step in result and update Localized fields
                    steps_list = (
                        current_preset.steps if current_preset else result.steps
                    )
                    for step in steps_list:
                        if step.id == step_id:
                            subsections = parse_subsections(content_text)
                            step.section.description.set(
                                lang, md_to_html(subsections["main"])
                            )
                            sub = extract_subtitle(subsections["main"])
                            if sub:
                                step.section.subtitle.set(lang, sub)
                            step.section.troubleshoot.set(
                                lang, md_to_html(subsections.get("troubleshoot", ""))
                            )
                            step.section.post_deploy.set(
                                lang, md_to_html(subsections.get("post_deploy", ""))
                            )
                            # Try to extract title from header
                            title_match = STEP_HEADER_PATTERN.match(current_step_header)
                            if title_match:
                                title = title_match.group(1).strip()
                                step.title.set(lang, title)
                                step.section.title.set(lang, title)
                            # Update wiring steps if present
                            if step.section.wiring and subsections.get("wiring"):
                                wiring_content = subsections["wiring"]
                                wiring_steps = []
                                for line in wiring_content.split("\n"):
                                    match = ORDERED_LIST_PATTERN.match(line.strip())
                                    if match:
                                        wiring_steps.append(match.group(1))
                                if wiring_steps:
                                    step.section.wiring.steps.set(lang, wiring_steps)
                            break

            current_step_header = None
            current_step_content = []

    def flush_preset_description():
        """Flush accumulated preset description."""
        nonlocal preset_description_lines
        if preset_description_lines and current_preset:
            desc_html = md_to_html("\n".join(preset_description_lines).strip())
            current_preset.description.set(lang, desc_html)
        preset_description_lines = []

    for line in lines:
        line_num += 1
        stripped = line.strip()

        # Check for success section
        if SUCCESS_HEADER_PATTERN.match(stripped):
            flush_step()
            flush_preset_description()
            current_section = "success"
            continue

        # Check for preset header
        preset_match = PRESET_HEADER_PATTERN.match(
            stripped
        ) or PRESET_HEADER_ZH_PATTERN.match(stripped)
        if preset_match:
            flush_step()
            flush_preset_description()
            if lang == "en":
                # Reset seen_step_ids for new preset (step IDs unique within preset)
                seen_step_ids.clear()
                preset_name = preset_match.group(1).strip()
                current_preset = PresetGuide(
                    id=preset_match.group(2),
                    name=Localized({"en": preset_name}),
                    description=Localized(),
                )
                result.presets.append(current_preset)
            else:
                # Update existing preset with new language name
                preset_id = preset_match.group(2)
                for p in result.presets:
                    if p.id == preset_id:
                        p.name.set(lang, preset_match.group(1).strip())
                        current_preset = p
                        break
            current_section = "preset"
            preset_description_lines = []
            continue

        # Check for step header
        step_match = STEP_HEADER_PATTERN.match(stripped)
        if step_match:
            flush_step()
            flush_preset_description()
            current_step_header = stripped
            current_step_line = line_num
            current_section = "step"
            continue

        # Accumulate content based on current section
        if current_section == "overview":
            overview_lines.append(line)
        elif current_section == "step":
            current_step_content.append(line)
        elif current_section == "success":
            success_lines.append(line)
        elif current_section == "preset" and not current_step_header:
            # Preset description before first step
            preset_description_lines.append(line)

    # Flush final step and description
    flush_step()
    flush_preset_description()

    # Set overview and success content
    result.overview.set(lang, md_to_html("\n".join(overview_lines).strip()))
    if success_lines:
        if not result.success:
            result.success = SuccessContent()
        result.success.content.set(lang, md_to_html("\n".join(success_lines).strip()))


def parse_bilingual_markdown(content: str, lang: str = "en") -> str:
    """Parse bilingual markdown and return content for specified language.

    Args:
        content: Raw markdown content with language markers
        lang: Target language ('en' or 'zh')

    Returns:
        Markdown content for the specified language
    """
    en_content, zh_content = split_by_language(content)

    if lang == "zh":
        return zh_content if zh_content else en_content
    return en_content if en_content else zh_content


def validate_deployment_guide(content: str) -> list[ParseError]:
    """Validate a deployment guide without fully parsing it.

    Returns list of validation errors.
    """
    result = parse_deployment_guide(content)
    return result.errors


def parse_single_language_guide(content: str, lang: str = "en") -> ParseResult:
    """Parse a single-language guide file (no language markers expected).

    This is used for parsing separate EN and ZH files.

    Args:
        content: Markdown content
        lang: Language code for this content (default: "en")

    Returns:
        ParseResult with Localized fields populated for the given language
    """
    result = ParseResult()

    if not content.strip():
        return result

    lines = content.split("\n")
    line_num = 0

    current_section = "overview"
    current_preset: Optional[PresetGuide] = None
    current_step_header: Optional[str] = None
    current_step_content: list[str] = []
    current_step_line: int = 0
    seen_step_ids: set[str] = set()

    overview_lines: list[str] = []
    success_lines: list[str] = []
    preset_completion_lines: list[str] = []
    preset_description_lines: list[str] = []

    def flush_step():
        """Process accumulated step content."""
        nonlocal current_step_header, current_step_content, current_step_line
        if current_step_header:
            content_text = "\n".join(current_step_content)
            step, errors, warnings = parse_deployment_step(
                current_step_header,
                content_text,
                "",  # No additional language content
                current_step_line,
            )
            result.errors.extend(errors)
            result.warnings.extend(warnings)
            if step:
                if step.id in seen_step_ids:
                    result.errors.append(
                        ParseError(
                            error_type=ParseErrorType.DUPLICATE_STEP_ID,
                            message=f"Duplicate step ID: {step.id}",
                            line_number=current_step_line,
                        )
                    )
                else:
                    seen_step_ids.add(step.id)
                    if current_preset:
                        current_preset.steps.append(step)
                    else:
                        result.steps.append(step)

            current_step_header = None
            current_step_content = []

    def flush_preset_completion():
        """Process accumulated preset completion content."""
        nonlocal preset_completion_lines
        if preset_completion_lines and current_preset:
            completion_html = md_to_html("\n".join(preset_completion_lines).strip())
            current_preset.completion = SuccessContent(
                content=Localized({lang: completion_html})
            )
        preset_completion_lines = []

    def flush_preset_description():
        """Flush accumulated preset description."""
        nonlocal preset_description_lines
        if preset_description_lines and current_preset:
            desc_html = md_to_html("\n".join(preset_description_lines).strip())
            current_preset.description.set(lang, desc_html)
        preset_description_lines = []

    for line in lines:
        line_num += 1
        stripped = line.strip()

        # Check for global success section (deprecated but kept for backward compatibility)
        if SUCCESS_HEADER_PATTERN.match(stripped):
            flush_step()
            flush_preset_description()
            flush_preset_completion()
            current_section = "success"
            continue

        # Check for preset completion section (### Deployment Complete / ### 部署完成)
        # Only at preset level (not inside a step — inside steps it's a subsection
        # handled by parse_subsections via post_deploy pattern)
        if PRESET_COMPLETION_PATTERN.match(stripped) and current_step_header is None:
            flush_step()
            flush_preset_description()
            current_section = "preset_completion"
            continue

        # Check for preset header (both EN and ZH patterns)
        preset_match = PRESET_HEADER_PATTERN.match(
            stripped
        ) or PRESET_HEADER_ZH_PATTERN.match(stripped)
        if preset_match:
            flush_step()
            flush_preset_description()
            flush_preset_completion()
            # Reset seen_step_ids for new preset
            seen_step_ids.clear()
            preset_name = preset_match.group(1).strip()
            current_preset = PresetGuide(
                id=preset_match.group(2),
                name=Localized({lang: preset_name}),
                description=Localized(),
            )
            result.presets.append(current_preset)
            current_section = "preset"
            preset_description_lines = []
            continue

        # Check for step header
        step_match = STEP_HEADER_PATTERN.match(stripped)
        if step_match:
            flush_step()
            flush_preset_description()
            current_step_header = stripped
            current_step_line = line_num
            current_section = "step"
            continue

        # Accumulate content based on current section
        if current_section == "overview":
            overview_lines.append(line)
        elif current_section == "step":
            current_step_content.append(line)
        elif current_section == "success":
            success_lines.append(line)
        elif current_section == "preset_completion":
            preset_completion_lines.append(line)
        elif current_section == "preset" and not current_step_header:
            preset_description_lines.append(line)

    # Flush final step and preset completion
    flush_step()
    flush_preset_description()
    flush_preset_completion()

    # Set overview and success content
    result.overview.set(lang, md_to_html("\n".join(overview_lines).strip()))
    if success_lines:
        result.success = SuccessContent(
            content=Localized({lang: md_to_html("\n".join(success_lines).strip())})
        )

    return result


def validate_structure_consistency(
    en_result: ParseResult, zh_result: ParseResult
) -> StructureValidationResult:
    """Validate that EN and ZH guide files have consistent structure.

    Checks:
    - Same number and order of presets
    - Same preset IDs
    - Same number and order of steps within each preset
    - Same step IDs, types, required flags, and config files
    """
    validation = StructureValidationResult()

    # Extract preset IDs
    validation.en_presets = [p.id for p in en_result.presets]
    validation.zh_presets = [p.id for p in zh_result.presets]

    # Extract steps by preset
    validation.en_steps_by_preset = {
        p.id: [(s.id, s.type, s.required, s.config_file) for s in p.steps]
        for p in en_result.presets
    }
    validation.zh_steps_by_preset = {
        p.id: [(s.id, s.type, s.required, s.config_file) for s in p.steps]
        for p in zh_result.presets
    }

    # Check preset count
    if len(validation.en_presets) != len(validation.zh_presets):
        validation.valid = False
        validation.errors.append(
            ParseError(
                error_type=ParseErrorType.PRESET_COUNT_MISMATCH,
                message=f"Preset count mismatch: EN has {len(validation.en_presets)}, ZH has {len(validation.zh_presets)}",
                suggestion="Ensure both guide.md and guide_zh.md have the same number of presets",
            )
        )

    # Check preset IDs and order
    for i, (en_id, zh_id) in enumerate(
        zip(validation.en_presets, validation.zh_presets)
    ):
        if en_id != zh_id:
            validation.valid = False
            validation.errors.append(
                ParseError(
                    error_type=ParseErrorType.PRESET_ID_MISMATCH,
                    message=f"Preset ID mismatch at position {i + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                    suggestion=f"Ensure preset IDs match: {{#{en_id}}} should be the same in both files",
                )
            )

    # Check steps within each preset
    for preset_id in validation.en_presets:
        if preset_id not in validation.zh_steps_by_preset:
            continue  # Already reported as preset mismatch

        en_steps = validation.en_steps_by_preset.get(preset_id, [])
        zh_steps = validation.zh_steps_by_preset.get(preset_id, [])

        # Check step count
        if len(en_steps) != len(zh_steps):
            validation.valid = False
            validation.errors.append(
                ParseError(
                    error_type=ParseErrorType.STEP_COUNT_MISMATCH,
                    message=f"Step count mismatch in preset '{preset_id}': EN has {len(en_steps)}, ZH has {len(zh_steps)}",
                    suggestion="Ensure both files have the same number of steps in this preset",
                )
            )
            continue

        # Check each step
        for j, (en_step, zh_step) in enumerate(zip(en_steps, zh_steps)):
            en_id, en_type, en_required, en_config = en_step
            zh_id, zh_type, zh_required, zh_config = zh_step

            if en_id != zh_id:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_ID_MISMATCH,
                        message=f"Step ID mismatch in preset '{preset_id}' at step {j + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                        suggestion=f"Ensure step ID {{#{en_id}}} matches in guide_zh.md",
                    )
                )

            if en_type != zh_type:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_TYPE_MISMATCH,
                        message=f"Step type mismatch for '{en_id}' in preset '{preset_id}': EN has type={en_type}, ZH has type={zh_type}",
                        suggestion=f"Ensure type={en_type} is the same in both files",
                    )
                )

            if en_required != zh_required:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_REQUIRED_MISMATCH,
                        message=f"Step required mismatch for '{en_id}' in preset '{preset_id}': EN has required={en_required}, ZH has required={zh_required}",
                        suggestion=f"Ensure required={'true' if en_required else 'false'} is the same in both files",
                    )
                )

            if en_config != zh_config:
                validation.valid = False
                validation.errors.append(
                    ParseError(
                        error_type=ParseErrorType.STEP_CONFIG_MISMATCH,
                        message=f"Step config mismatch for '{en_id}' in preset '{preset_id}': EN has config={en_config}, ZH has config={zh_config}",
                        suggestion=f"Ensure config={en_config} is the same in both files",
                    )
                )

    return validation


def _merge_localized(base: Localized, other: Localized, lang: str) -> None:
    """Merge content from other Localized into base for the specified language."""
    value = other.get(lang)
    if value is not None:
        base.set(lang, value)


def parse_guide_multilang(
    lang_contents: Dict[str, str],
) -> tuple[ParseResult, StructureValidationResult]:
    """Parse multiple language guide files and validate structure consistency.

    Args:
        lang_contents: Dict mapping language code to file content
                      e.g., {"en": content_en, "zh": content_zh, "ja": content_ja}

    Returns:
        Tuple of (merged ParseResult, StructureValidationResult)
    """
    if not lang_contents:
        return ParseResult(), StructureValidationResult()

    # Parse each language file separately
    results: Dict[str, ParseResult] = {}
    for lang, content in lang_contents.items():
        results[lang] = parse_single_language_guide(content, lang)

    # Select base language (prefer "en", otherwise first available)
    base_lang = "en" if "en" in results else list(results.keys())[0]
    base_result = results[base_lang]

    # Validate structure consistency (compare all against base)
    validation = StructureValidationResult(valid=True)
    for lang, result in results.items():
        if lang != base_lang:
            lang_validation = validate_structure_consistency(base_result, result)
            if not lang_validation.valid:
                validation.valid = False
                validation.errors.extend(lang_validation.errors)
            validation.warnings.extend(lang_validation.warnings)

    # Create merged result
    merged = ParseResult(
        overview=Localized(),
        errors=sum((r.errors for r in results.values()), []),
        warnings=sum((r.warnings for r in results.values()), []),
    )

    # Merge overview from all languages
    for lang, result in results.items():
        overview_content = result.overview.get(lang)
        if overview_content:
            merged.overview.set(lang, overview_content)

    # Merge presets
    for base_preset in base_result.presets:
        merged_preset = PresetGuide(
            id=base_preset.id,
            name=Localized(),
            description=Localized(),
            is_default=base_preset.is_default,
        )

        # Merge preset names and descriptions from all languages
        for lang, result in results.items():
            lang_preset = next(
                (p for p in result.presets if p.id == base_preset.id), None
            )
            if lang_preset:
                name = lang_preset.name.get(lang)
                if name:
                    merged_preset.name.set(lang, name)
                desc = lang_preset.description.get(lang)
                if desc:
                    merged_preset.description.set(lang, desc)

        # Merge steps
        for base_step in base_preset.steps:
            merged_step = DeploymentStep(
                id=base_step.id,
                title=Localized(),
                type=base_step.type,
                required=base_step.required,
                config_file=base_step.config_file,
                section=SectionContent(
                    title=Localized(),
                    subtitle=Localized(),
                    description=Localized(),
                    troubleshoot=Localized(),
                    post_deploy=Localized(),
                    wiring=None,
                ),
            )

            # Merge step content from all languages
            for lang, result in results.items():
                lang_preset = next(
                    (p for p in result.presets if p.id == base_preset.id), None
                )
                if lang_preset:
                    lang_step = next(
                        (s for s in lang_preset.steps if s.id == base_step.id), None
                    )
                    if lang_step:
                        # Merge title
                        title = lang_step.title.get(lang)
                        if title:
                            merged_step.title.set(lang, title)
                            merged_step.section.title.set(lang, title)
                        # Merge subtitle
                        sub = lang_step.section.subtitle.get(lang)
                        if sub:
                            merged_step.section.subtitle.set(lang, sub)
                        # Merge description
                        desc = lang_step.section.description.get(lang)
                        if desc:
                            merged_step.section.description.set(lang, desc)
                        # Merge troubleshoot
                        troubleshoot = lang_step.section.troubleshoot.get(lang)
                        if troubleshoot:
                            merged_step.section.troubleshoot.set(lang, troubleshoot)
                        # Merge post_deploy
                        post_deploy = lang_step.section.post_deploy.get(lang)
                        if post_deploy:
                            merged_step.section.post_deploy.set(lang, post_deploy)
                        # Merge wiring (image from base, steps from all languages)
                        if lang_step.section.wiring:
                            if merged_step.section.wiring is None:
                                merged_step.section.wiring = WiringInfo(
                                    image=lang_step.section.wiring.image,
                                    steps=Localized(),
                                )
                            wiring_steps = lang_step.section.wiring.steps.get(lang)
                            if wiring_steps:
                                merged_step.section.wiring.steps.set(lang, wiring_steps)

            # Merge targets
            if base_step.targets:
                merged_targets = []
                for base_target in base_step.targets:
                    merged_target = TargetInfo(
                        id=base_target.id,
                        name=Localized(),
                        config_file=base_target.config_file,
                        default=base_target.default,
                        target_type=base_target.target_type,
                        description=Localized(),
                        description_html=Localized(),
                        troubleshoot=Localized(),
                        post_deploy=Localized(),
                        wiring=None,
                    )

                    # Merge target content from all languages
                    for lang, result in results.items():
                        lang_preset = next(
                            (p for p in result.presets if p.id == base_preset.id), None
                        )
                        if lang_preset:
                            lang_step = next(
                                (s for s in lang_preset.steps if s.id == base_step.id),
                                None,
                            )
                            if lang_step:
                                lang_target = next(
                                    (
                                        t
                                        for t in lang_step.targets
                                        if t.id == base_target.id
                                    ),
                                    None,
                                )
                                if lang_target:
                                    # Merge name
                                    name = lang_target.name.get(lang)
                                    if name:
                                        merged_target.name.set(lang, name)
                                    # Merge descriptions
                                    desc = lang_target.description.get(lang)
                                    if desc:
                                        merged_target.description.set(lang, desc)
                                    desc_html = lang_target.description_html.get(lang)
                                    if desc_html:
                                        merged_target.description_html.set(
                                            lang, desc_html
                                        )
                                    # Merge troubleshoot
                                    troubleshoot = lang_target.troubleshoot.get(lang)
                                    if troubleshoot:
                                        merged_target.troubleshoot.set(
                                            lang, troubleshoot
                                        )
                                    # Merge post_deploy
                                    post_deploy = lang_target.post_deploy.get(lang)
                                    if post_deploy:
                                        merged_target.post_deploy.set(lang, post_deploy)
                                    # Merge wiring
                                    if lang_target.wiring:
                                        if merged_target.wiring is None:
                                            merged_target.wiring = WiringInfo(
                                                image=lang_target.wiring.image,
                                                steps=Localized(),
                                            )
                                        wiring_steps = lang_target.wiring.steps.get(
                                            lang
                                        )
                                        if wiring_steps:
                                            merged_target.wiring.steps.set(
                                                lang, wiring_steps
                                            )

                    merged_targets.append(merged_target)
                merged_step.targets = merged_targets

            merged_preset.steps.append(merged_step)

        # Merge preset completion
        for lang, result in results.items():
            lang_preset = next(
                (p for p in result.presets if p.id == base_preset.id), None
            )
            if lang_preset and lang_preset.completion:
                if merged_preset.completion is None:
                    merged_preset.completion = SuccessContent(content=Localized())
                content = lang_preset.completion.content.get(lang)
                if content:
                    merged_preset.completion.content.set(lang, content)

        merged.presets.append(merged_preset)

    # Merge success content
    for lang, result in results.items():
        if result.success:
            if merged.success is None:
                merged.success = SuccessContent(content=Localized())
            content = result.success.content.get(lang)
            if content:
                merged.success.content.set(lang, content)

    return merged, validation


def parse_guide_pair(
    en_content: str, zh_content: str
) -> tuple[ParseResult, StructureValidationResult]:
    """Parse a pair of EN and ZH guide files and validate structure consistency.

    This is a convenience wrapper around parse_guide_multilang for the common
    bilingual (English/Chinese) case.

    Args:
        en_content: Content of guide.md (English)
        zh_content: Content of guide_zh.md (Chinese)

    Returns:
        Tuple of (merged ParseResult, StructureValidationResult)
    """
    return parse_guide_multilang({"en": en_content, "zh": zh_content})
