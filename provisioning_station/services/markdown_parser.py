"""
Bilingual Markdown Parser for Solution Documentation.

This module provides parsing utilities for bilingual markdown format.
Supports both:
1. Combined format: Single file with `<!-- @lang:xx -->` markers
2. Separate format: Two files (guide.md + guide_zh.md) with structure validation

Format specification:
- Deployment steps use H2 headers with metadata: `## Step N: Title {#step_id type=xxx required=true}`
- Preset sections: `## Preset: Name {#preset_id}` / `## 套餐: 名称 {#preset_id}`
- Sub-sections: `### Prerequisites`, `### Wiring`, `### Troubleshooting`
- Success section starts with `# Deployment Complete` / `# 部署完成`
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import markdown


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
    steps: list[str] = field(default_factory=list)
    steps_zh: list[str] = field(default_factory=list)


@dataclass
class TargetInfo:
    """Target information for docker_deploy type devices."""
    id: str
    name: str
    name_zh: str
    config_file: Optional[str] = None
    default: bool = False
    target_type: str = "local"  # "local" or "remote"
    description: str = ""
    description_zh: str = ""
    troubleshoot: str = ""
    troubleshoot_zh: str = ""
    wiring: Optional["WiringInfo"] = None


@dataclass
class SectionContent:
    """Section content compatible with existing frontend structure."""
    title: str = ""
    title_zh: str = ""
    description: str = ""
    description_zh: str = ""
    troubleshoot: str = ""
    troubleshoot_zh: str = ""
    wiring: Optional[WiringInfo] = None


@dataclass
class DeploymentStep:
    """A parsed deployment step from the markdown."""
    id: str
    title_en: str
    title_zh: str
    type: str
    required: bool = True
    config_file: Optional[str] = None
    section: SectionContent = field(default_factory=SectionContent)
    targets: list[TargetInfo] = field(default_factory=list)


@dataclass
class PresetGuide:
    """A parsed preset guide section."""
    id: str
    name: str
    name_zh: str
    description: str = ""
    description_zh: str = ""
    steps: list[DeploymentStep] = field(default_factory=list)


@dataclass
class SuccessContent:
    """Parsed success/completion content."""
    content_en: str = ""
    content_zh: str = ""


@dataclass
class ParseResult:
    """Result of parsing a deployment guide markdown file."""
    overview_en: str = ""
    overview_zh: str = ""
    presets: list[PresetGuide] = field(default_factory=list)
    steps: list[DeploymentStep] = field(default_factory=list)  # Steps without preset context
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
    en_steps_by_preset: dict = field(default_factory=dict)  # preset_id -> list of step IDs
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
}

# Regex patterns
LANG_MARKER_PATTERN = re.compile(r'<!--\s*@lang:(\w+)\s*-->')
STEP_HEADER_PATTERN = re.compile(
    r'^##\s+(?:Step\s+\d+:\s*|步骤\s*\d+[：:]\s*)?(.+?)\s*\{#(\w+)([^}]*)\}\s*$',
    re.IGNORECASE
)
PRESET_HEADER_PATTERN = re.compile(
    r'^##\s+Preset:\s*(.+?)\s*\{#(\w+)\}\s*$',
    re.IGNORECASE
)
PRESET_HEADER_ZH_PATTERN = re.compile(
    r'^##\s+套餐[：:]\s*(.+?)\s*\{#(\w+)\}\s*$',
    re.IGNORECASE
)
TARGET_HEADER_PATTERN = re.compile(
    r'^###\s+(?:Target|部署目标)[：:]?\s*(.+?)\s*\{#(\w+)([^}]*)\}\s*$',
    re.IGNORECASE
)
SUCCESS_HEADER_PATTERN = re.compile(
    r'^#\s+(Deployment\s+Complete|部署完成)\s*$',
    re.IGNORECASE
)
SUBSECTION_PATTERNS = {
    'prerequisites': re.compile(r'^###\s+(Prerequisites|前置条件)\s*$', re.IGNORECASE),
    'wiring': re.compile(r'^###\s+(Wiring|接线)\s*$', re.IGNORECASE),
    'troubleshoot': re.compile(r'^###\s+(Troubleshooting|故障排除)\s*$', re.IGNORECASE),
}
IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
ORDERED_LIST_PATTERN = re.compile(r'^\d+\.\s+(.+)$')


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
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
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
            lang = parts[i].strip().lower() if parts[i].strip() in ('en', 'zh') else None
            if lang:
                text = parts[i + 1] if i + 1 < len(parts) else ""
                if lang == 'en':
                    english = text.strip()
                elif lang == 'zh':
                    chinese = text.strip()
                i += 2
                continue
        i += 1

    return english, chinese


def extract_wiring(content: str, content_zh: str = "") -> Optional[WiringInfo]:
    """Extract wiring information from content."""
    wiring = WiringInfo()

    # Extract image
    img_match = IMAGE_PATTERN.search(content)
    if img_match:
        wiring.image = img_match.group(2)

    # Extract ordered list steps
    for line in content.split('\n'):
        match = ORDERED_LIST_PATTERN.match(line.strip())
        if match:
            wiring.steps.append(match.group(1))

    # Extract Chinese steps
    if content_zh:
        for line in content_zh.split('\n'):
            match = ORDERED_LIST_PATTERN.match(line.strip())
            if match:
                wiring.steps_zh.append(match.group(1))

    if wiring.image or wiring.steps:
        return wiring
    return None


def md_to_html(content: str) -> str:
    """Convert markdown content to HTML."""
    if not content.strip():
        return ""
    return markdown.markdown(
        content,
        extensions=['tables', 'fenced_code', 'nl2br']
    )


def parse_subsections(content: str) -> dict[str, str]:
    """Parse subsections (Prerequisites, Wiring, Troubleshooting) from step content.

    Returns dict with keys: 'main', 'prerequisites', 'wiring', 'troubleshoot'
    """
    result = {
        'main': '',
        'prerequisites': '',
        'wiring': '',
        'troubleshoot': ''
    }

    lines = content.split('\n')
    current_section = 'main'
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
        result[key] = '\n'.join(lines_list).strip()

    return result


def parse_deployment_step(
    header_line: str,
    content_en: str,
    content_zh: str,
    line_number: int
) -> tuple[Optional[DeploymentStep], list[ParseError], list[ParseWarning]]:
    """Parse a single deployment step from header and content.

    Returns (step, errors, warnings).
    """
    errors = []
    warnings = []

    # Parse header
    match = STEP_HEADER_PATTERN.match(header_line.strip())
    if not match:
        errors.append(ParseError(
            error_type=ParseErrorType.INVALID_STEP_FORMAT,
            message=f"Invalid step header format: {header_line}",
            line_number=line_number,
            suggestion="Use format: ## Step N: Title {#step_id type=xxx required=true}"
        ))
        return None, errors, warnings

    title = match.group(1).strip()
    step_id = match.group(2)
    attrs_str = match.group(3)
    attrs = parse_step_attributes(attrs_str)

    # Validate type
    step_type = attrs.get('type', '')
    if not step_type:
        errors.append(ParseError(
            error_type=ParseErrorType.MISSING_REQUIRED_FIELD,
            message=f"Step '{step_id}' missing required 'type' attribute",
            line_number=line_number,
            suggestion=f"Add type=xxx where xxx is one of: {', '.join(sorted(VALID_STEP_TYPES))}"
        ))
        return None, errors, warnings

    if step_type not in VALID_STEP_TYPES:
        errors.append(ParseError(
            error_type=ParseErrorType.INVALID_STEP_TYPE,
            message=f"Invalid step type '{step_type}' for step '{step_id}'",
            line_number=line_number,
            suggestion=f"Valid types: {', '.join(sorted(VALID_STEP_TYPES))}"
        ))
        return None, errors, warnings

    # Parse content subsections
    subsections_en = parse_subsections(content_en)
    subsections_zh = parse_subsections(content_zh)

    # Extract Chinese title from Chinese content header
    title_zh = title  # Default to English title
    zh_lines = content_zh.strip().split('\n') if content_zh else []

    # Check for translation warning
    if not content_zh.strip():
        warnings.append(ParseWarning(
            message=f"Step '{step_id}' missing Chinese translation",
            line_number=line_number
        ))

    # Build section content
    section = SectionContent(
        title=title,
        title_zh=title_zh,
        description=md_to_html(subsections_en['main']),
        description_zh=md_to_html(subsections_zh.get('main', '')),
        troubleshoot=md_to_html(subsections_en.get('troubleshoot', '')),
        troubleshoot_zh=md_to_html(subsections_zh.get('troubleshoot', '')),
    )

    # Extract wiring if present
    if subsections_en.get('wiring'):
        section.wiring = extract_wiring(
            subsections_en['wiring'],
            subsections_zh.get('wiring', '')
        )

    step = DeploymentStep(
        id=step_id,
        title_en=title,
        title_zh=title_zh,
        type=step_type,
        required=attrs.get('required', True),
        config_file=attrs.get('config'),
        section=section
    )

    # Parse targets (for docker_deploy and recamera_cpp types)
    if step_type in ('docker_deploy', 'recamera_cpp'):
        targets = parse_targets(content_en, content_zh)
        if targets:
            step.targets = targets

    return step, errors, warnings


def parse_targets(content_en: str, content_zh: str) -> list[TargetInfo]:
    """Parse target sections from step content (for docker_deploy and recamera_cpp types).

    Target format: ### Target: Name {#id config=xxx default=true}
    Content below each target header is the description + wiring steps.
    """
    targets = []

    def parse_target_content(content_lines: list[str]) -> tuple[str, list[str], Optional[str]]:
        """Parse target content into description, wiring steps, and wiring image."""
        description_lines = []
        wiring_steps = []
        wiring_image = None
        in_wiring = False

        for line in content_lines:
            stripped = line.strip()
            # Check for separator (end of target)
            if stripped == '---':
                break
            # Check for next subsection header that's not a target
            if stripped.startswith('###') and not TARGET_HEADER_PATTERN.match(stripped):
                in_wiring = True
                continue
            # Parse wiring content
            if in_wiring:
                # Extract image
                img_match = IMAGE_PATTERN.match(stripped)
                if img_match:
                    wiring_image = img_match.group(2)
                    continue
                # Extract ordered list steps
                list_match = ORDERED_LIST_PATTERN.match(stripped)
                if list_match:
                    wiring_steps.append(list_match.group(1))
                    continue
            else:
                # Check for inline image (wiring diagram)
                img_match = IMAGE_PATTERN.match(stripped)
                if img_match:
                    wiring_image = img_match.group(2)
                    continue
                # Check for ordered list (wiring steps)
                list_match = ORDERED_LIST_PATTERN.match(stripped)
                if list_match:
                    wiring_steps.append(list_match.group(1))
                    continue
                # Regular description content
                description_lines.append(line)

        return '\n'.join(description_lines).strip(), wiring_steps, wiring_image

    # Split EN content by target headers
    en_lines = content_en.split('\n')
    current_target_id = None
    current_target_name = ""
    current_attrs = {}
    current_content: list[str] = []

    for line in en_lines:
        match = TARGET_HEADER_PATTERN.match(line.strip())
        if match:
            # Save previous target if exists
            if current_target_id:
                desc, wiring_steps, wiring_image = parse_target_content(current_content)
                wiring = None
                if wiring_image or wiring_steps:
                    wiring = WiringInfo(
                        image=wiring_image,
                        steps=wiring_steps,
                        steps_zh=[],  # Will be updated from zh content
                    )
                target = TargetInfo(
                    id=current_target_id,
                    name=current_target_name,
                    name_zh=current_target_name,  # Will be updated from zh content
                    config_file=current_attrs.get('config'),
                    default=current_attrs.get('default', False),
                    target_type=current_attrs.get('type', 'local'),
                    description=desc.strip() if desc else "",  # Plain text for selector
                    wiring=wiring,
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
        desc, wiring_steps, wiring_image = parse_target_content(current_content)
        wiring = None
        if wiring_image or wiring_steps:
            wiring = WiringInfo(
                image=wiring_image,
                steps=wiring_steps,
                steps_zh=[],
            )
        target = TargetInfo(
            id=current_target_id,
            name=current_target_name,
            name_zh=current_target_name,
            config_file=current_attrs.get('config'),
            default=current_attrs.get('default', False),
            target_type=current_attrs.get('type', 'local'),
            description=desc.strip() if desc else "",  # Plain text for selector
            wiring=wiring,
        )
        targets.append(target)

    # Parse Chinese content to update translations
    if content_zh and targets:
        zh_lines = content_zh.split('\n')
        zh_target_idx = 0
        current_zh_content: list[str] = []
        current_zh_name = ""

        for line in zh_lines:
            match = TARGET_HEADER_PATTERN.match(line.strip())
            if match:
                # Update previous target with ZH content
                if zh_target_idx > 0 and zh_target_idx <= len(targets):
                    target = targets[zh_target_idx - 1]
                    target.name_zh = current_zh_name
                    desc, wiring_steps_zh, _ = parse_target_content(current_zh_content)
                    if desc:
                        target.description_zh = desc.strip()  # Plain text for selector
                    # Update wiring steps_zh if target has wiring
                    if target.wiring and wiring_steps_zh:
                        target.wiring.steps_zh = wiring_steps_zh

                current_zh_name = match.group(1).strip()
                current_zh_content = []
                zh_target_idx += 1
            else:
                if zh_target_idx > 0:
                    current_zh_content.append(line)

        # Update last target
        if zh_target_idx > 0 and zh_target_idx <= len(targets):
            target = targets[zh_target_idx - 1]
            target.name_zh = current_zh_name
            desc, wiring_steps_zh, _ = parse_target_content(current_zh_content)
            if desc:
                target.description_zh = desc.strip()  # Plain text for selector
            if target.wiring and wiring_steps_zh:
                target.wiring.steps_zh = wiring_steps_zh

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
        result.warnings.append(ParseWarning(
            message="No language markers found. Using entire content as English."
        ))

    # Parse English content
    _parse_guide_content(content_en, 'en', result)

    # Parse Chinese content to add translations
    if content_zh:
        _parse_guide_content(content_zh, 'zh', result)

    return result


def _find_matching_step_in_zh(step_id: str, zh_steps: list[dict]) -> Optional[dict]:
    """Find matching step content in Chinese parsed content."""
    for s in zh_steps:
        if s.get('id') == step_id:
            return s
    return None


def _parse_guide_content(content: str, lang: str, result: ParseResult) -> None:
    """Parse guide content for a specific language and update result."""
    lines = content.split('\n')
    line_num = 0

    current_section = 'overview'  # overview, preset, step, success
    current_preset: Optional[PresetGuide] = None
    current_step_header: Optional[str] = None
    current_step_content: list[str] = []
    current_step_line: int = 0
    seen_step_ids: set[str] = set()

    overview_lines: list[str] = []
    success_lines: list[str] = []

    def flush_step():
        """Process accumulated step content."""
        nonlocal current_step_header, current_step_content, current_step_line
        if current_step_header:
            content_text = '\n'.join(current_step_content)
            if lang == 'en':
                step, errors, warnings = parse_deployment_step(
                    current_step_header,
                    content_text,
                    "",  # zh content added later
                    current_step_line
                )
                result.errors.extend(errors)
                result.warnings.extend(warnings)
                if step:
                    if step.id in seen_step_ids:
                        result.errors.append(ParseError(
                            error_type=ParseErrorType.DUPLICATE_STEP_ID,
                            message=f"Duplicate step ID: {step.id}",
                            line_number=current_step_line
                        ))
                    else:
                        seen_step_ids.add(step.id)
                        if current_preset:
                            current_preset.steps.append(step)
                        else:
                            result.steps.append(step)
            else:
                # Update existing step with Chinese content
                step_id_match = STEP_HEADER_PATTERN.match(current_step_header)
                if step_id_match:
                    step_id = step_id_match.group(2)
                    # Find step in result and update zh fields
                    steps_list = current_preset.steps if current_preset else result.steps
                    for step in steps_list:
                        if step.id == step_id:
                            subsections = parse_subsections(content_text)
                            step.section.description_zh = md_to_html(subsections['main'])
                            step.section.troubleshoot_zh = md_to_html(subsections.get('troubleshoot', ''))
                            # Try to extract Chinese title from header
                            title_match = STEP_HEADER_PATTERN.match(current_step_header)
                            if title_match:
                                step.title_zh = title_match.group(1).strip()
                                step.section.title_zh = step.title_zh
                            # Update wiring Chinese steps if present
                            if step.section.wiring and subsections.get('wiring'):
                                wiring_content = subsections['wiring']
                                for line in wiring_content.split('\n'):
                                    match = ORDERED_LIST_PATTERN.match(line.strip())
                                    if match:
                                        step.section.wiring.steps_zh.append(match.group(1))
                            break

            current_step_header = None
            current_step_content = []

    for line in lines:
        line_num += 1
        stripped = line.strip()

        # Check for success section
        if SUCCESS_HEADER_PATTERN.match(stripped):
            flush_step()
            current_section = 'success'
            continue

        # Check for preset header
        preset_match = PRESET_HEADER_PATTERN.match(stripped) or PRESET_HEADER_ZH_PATTERN.match(stripped)
        if preset_match:
            flush_step()
            if lang == 'en':
                # Reset seen_step_ids for new preset (step IDs unique within preset)
                seen_step_ids.clear()
                current_preset = PresetGuide(
                    id=preset_match.group(2),
                    name=preset_match.group(1).strip(),
                    name_zh=preset_match.group(1).strip()
                )
                result.presets.append(current_preset)
            else:
                # Update existing preset with Chinese name
                preset_id = preset_match.group(2)
                for p in result.presets:
                    if p.id == preset_id:
                        p.name_zh = preset_match.group(1).strip()
                        current_preset = p
                        break
            current_section = 'preset'
            continue

        # Check for step header
        step_match = STEP_HEADER_PATTERN.match(stripped)
        if step_match:
            flush_step()
            current_step_header = stripped
            current_step_line = line_num
            current_section = 'step'
            continue

        # Accumulate content based on current section
        if current_section == 'overview':
            overview_lines.append(line)
        elif current_section == 'step':
            current_step_content.append(line)
        elif current_section == 'success':
            success_lines.append(line)
        elif current_section == 'preset' and not current_step_header:
            # Preset description before first step
            if current_preset and lang == 'en':
                current_preset.description += line + '\n'
            elif current_preset:
                current_preset.description_zh += line + '\n'

    # Flush final step
    flush_step()

    # Set overview and success content
    if lang == 'en':
        result.overview_en = md_to_html('\n'.join(overview_lines).strip())
        if success_lines:
            if not result.success:
                result.success = SuccessContent()
            result.success.content_en = md_to_html('\n'.join(success_lines).strip())
        # Convert preset descriptions to HTML
        for preset in result.presets:
            if preset.description:
                preset.description = md_to_html(preset.description.strip())
    else:
        result.overview_zh = md_to_html('\n'.join(overview_lines).strip())
        if success_lines:
            if not result.success:
                result.success = SuccessContent()
            result.success.content_zh = md_to_html('\n'.join(success_lines).strip())
        # Convert preset descriptions to HTML
        for preset in result.presets:
            if preset.description_zh:
                preset.description_zh = md_to_html(preset.description_zh.strip())


def parse_bilingual_markdown(content: str, lang: str = 'en') -> str:
    """Parse bilingual markdown and return content for specified language.

    Args:
        content: Raw markdown content with language markers
        lang: Target language ('en' or 'zh')

    Returns:
        Markdown content for the specified language
    """
    en_content, zh_content = split_by_language(content)

    if lang == 'zh':
        return zh_content if zh_content else en_content
    return en_content if en_content else zh_content


def validate_deployment_guide(content: str) -> list[ParseError]:
    """Validate a deployment guide without fully parsing it.

    Returns list of validation errors.
    """
    result = parse_deployment_guide(content)
    return result.errors


def parse_single_language_guide(content: str) -> ParseResult:
    """Parse a single-language guide file (no language markers expected).

    This is used for parsing separate EN and ZH files.
    """
    result = ParseResult()

    if not content.strip():
        return result

    lines = content.split('\n')
    line_num = 0

    current_section = 'overview'
    current_preset: Optional[PresetGuide] = None
    current_step_header: Optional[str] = None
    current_step_content: list[str] = []
    current_step_line: int = 0
    seen_step_ids: set[str] = set()

    overview_lines: list[str] = []
    success_lines: list[str] = []

    def flush_step():
        """Process accumulated step content."""
        nonlocal current_step_header, current_step_content, current_step_line
        if current_step_header:
            content_text = '\n'.join(current_step_content)
            step, errors, warnings = parse_deployment_step(
                current_step_header,
                content_text,
                "",  # No zh content for single-language parse
                current_step_line
            )
            result.errors.extend(errors)
            result.warnings.extend(warnings)
            if step:
                if step.id in seen_step_ids:
                    result.errors.append(ParseError(
                        error_type=ParseErrorType.DUPLICATE_STEP_ID,
                        message=f"Duplicate step ID: {step.id}",
                        line_number=current_step_line
                    ))
                else:
                    seen_step_ids.add(step.id)
                    if current_preset:
                        current_preset.steps.append(step)
                    else:
                        result.steps.append(step)

            current_step_header = None
            current_step_content = []

    for line in lines:
        line_num += 1
        stripped = line.strip()

        # Check for success section
        if SUCCESS_HEADER_PATTERN.match(stripped):
            flush_step()
            current_section = 'success'
            continue

        # Check for preset header (both EN and ZH patterns)
        preset_match = PRESET_HEADER_PATTERN.match(stripped) or PRESET_HEADER_ZH_PATTERN.match(stripped)
        if preset_match:
            flush_step()
            # Reset seen_step_ids for new preset
            seen_step_ids.clear()
            current_preset = PresetGuide(
                id=preset_match.group(2),
                name=preset_match.group(1).strip(),
                name_zh=preset_match.group(1).strip()
            )
            result.presets.append(current_preset)
            current_section = 'preset'
            continue

        # Check for step header
        step_match = STEP_HEADER_PATTERN.match(stripped)
        if step_match:
            flush_step()
            current_step_header = stripped
            current_step_line = line_num
            current_section = 'step'
            continue

        # Accumulate content based on current section
        if current_section == 'overview':
            overview_lines.append(line)
        elif current_section == 'step':
            current_step_content.append(line)
        elif current_section == 'success':
            success_lines.append(line)
        elif current_section == 'preset' and not current_step_header:
            if current_preset:
                current_preset.description += line + '\n'

    # Flush final step
    flush_step()

    # Set overview and success content
    result.overview_en = md_to_html('\n'.join(overview_lines).strip())
    if success_lines:
        result.success = SuccessContent(content_en=md_to_html('\n'.join(success_lines).strip()))

    # Convert preset descriptions to HTML
    for preset in result.presets:
        if preset.description:
            preset.description = md_to_html(preset.description.strip())

    return result


def validate_structure_consistency(
    en_result: ParseResult,
    zh_result: ParseResult
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
        validation.errors.append(ParseError(
            error_type=ParseErrorType.PRESET_COUNT_MISMATCH,
            message=f"Preset count mismatch: EN has {len(validation.en_presets)}, ZH has {len(validation.zh_presets)}",
            suggestion="Ensure both guide.md and guide_zh.md have the same number of presets"
        ))

    # Check preset IDs and order
    for i, (en_id, zh_id) in enumerate(zip(validation.en_presets, validation.zh_presets)):
        if en_id != zh_id:
            validation.valid = False
            validation.errors.append(ParseError(
                error_type=ParseErrorType.PRESET_ID_MISMATCH,
                message=f"Preset ID mismatch at position {i + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                suggestion=f"Ensure preset IDs match: {{#{en_id}}} should be the same in both files"
            ))

    # Check steps within each preset
    for preset_id in validation.en_presets:
        if preset_id not in validation.zh_steps_by_preset:
            continue  # Already reported as preset mismatch

        en_steps = validation.en_steps_by_preset.get(preset_id, [])
        zh_steps = validation.zh_steps_by_preset.get(preset_id, [])

        # Check step count
        if len(en_steps) != len(zh_steps):
            validation.valid = False
            validation.errors.append(ParseError(
                error_type=ParseErrorType.STEP_COUNT_MISMATCH,
                message=f"Step count mismatch in preset '{preset_id}': EN has {len(en_steps)}, ZH has {len(zh_steps)}",
                suggestion="Ensure both files have the same number of steps in this preset"
            ))
            continue

        # Check each step
        for j, (en_step, zh_step) in enumerate(zip(en_steps, zh_steps)):
            en_id, en_type, en_required, en_config = en_step
            zh_id, zh_type, zh_required, zh_config = zh_step

            if en_id != zh_id:
                validation.valid = False
                validation.errors.append(ParseError(
                    error_type=ParseErrorType.STEP_ID_MISMATCH,
                    message=f"Step ID mismatch in preset '{preset_id}' at step {j + 1}: EN has '{en_id}', ZH has '{zh_id}'",
                    suggestion=f"Ensure step ID {{#{en_id}}} matches in guide_zh.md"
                ))

            if en_type != zh_type:
                validation.valid = False
                validation.errors.append(ParseError(
                    error_type=ParseErrorType.STEP_TYPE_MISMATCH,
                    message=f"Step type mismatch for '{en_id}' in preset '{preset_id}': EN has type={en_type}, ZH has type={zh_type}",
                    suggestion=f"Ensure type={en_type} is the same in both files"
                ))

            if en_required != zh_required:
                validation.valid = False
                validation.errors.append(ParseError(
                    error_type=ParseErrorType.STEP_REQUIRED_MISMATCH,
                    message=f"Step required mismatch for '{en_id}' in preset '{preset_id}': EN has required={en_required}, ZH has required={zh_required}",
                    suggestion=f"Ensure required={'true' if en_required else 'false'} is the same in both files"
                ))

            if en_config != zh_config:
                validation.valid = False
                validation.errors.append(ParseError(
                    error_type=ParseErrorType.STEP_CONFIG_MISMATCH,
                    message=f"Step config mismatch for '{en_id}' in preset '{preset_id}': EN has config={en_config}, ZH has config={zh_config}",
                    suggestion=f"Ensure config={en_config} is the same in both files"
                ))

    return validation


def parse_guide_pair(en_content: str, zh_content: str) -> tuple[ParseResult, StructureValidationResult]:
    """Parse a pair of EN and ZH guide files and validate structure consistency.

    Args:
        en_content: Content of guide.md (English)
        zh_content: Content of guide_zh.md (Chinese)

    Returns:
        Tuple of (merged ParseResult, StructureValidationResult)
    """
    # Parse each file separately
    en_result = parse_single_language_guide(en_content)
    zh_result = parse_single_language_guide(zh_content)

    # Validate structure consistency
    validation = validate_structure_consistency(en_result, zh_result)

    # Merge results - use EN as base, add ZH translations
    merged = ParseResult(
        overview_en=en_result.overview_en,
        overview_zh=zh_result.overview_en,  # zh_result.overview_en contains the ZH overview
        errors=en_result.errors + zh_result.errors,
        warnings=en_result.warnings + zh_result.warnings,
    )

    # Merge presets
    for en_preset in en_result.presets:
        # Find corresponding ZH preset
        zh_preset = next((p for p in zh_result.presets if p.id == en_preset.id), None)

        merged_preset = PresetGuide(
            id=en_preset.id,
            name=en_preset.name,
            name_zh=zh_preset.name if zh_preset else en_preset.name,
            description=en_preset.description,
            description_zh=zh_preset.description if zh_preset else "",
        )

        # Merge steps
        for en_step in en_preset.steps:
            # Find corresponding ZH step
            zh_step = None
            if zh_preset:
                zh_step = next((s for s in zh_preset.steps if s.id == en_step.id), None)

            merged_step = DeploymentStep(
                id=en_step.id,
                title_en=en_step.title_en,
                title_zh=zh_step.title_en if zh_step else en_step.title_en,
                type=en_step.type,
                required=en_step.required,
                config_file=en_step.config_file,
                section=SectionContent(
                    title=en_step.section.title,
                    title_zh=zh_step.section.title if zh_step else en_step.section.title,
                    description=en_step.section.description,
                    description_zh=zh_step.section.description if zh_step else "",
                    troubleshoot=en_step.section.troubleshoot,
                    troubleshoot_zh=zh_step.section.troubleshoot if zh_step else "",
                    wiring=en_step.section.wiring,
                ),
            )
            merged_preset.steps.append(merged_step)

        merged.presets.append(merged_preset)

    # Merge success content
    if en_result.success or zh_result.success:
        merged.success = SuccessContent(
            content_en=en_result.success.content_en if en_result.success else "",
            content_zh=zh_result.success.content_en if zh_result.success else "",
        )

    return merged, validation
