"""
Template variable substitution and command building utilities.

Shared by action_executor, docker_remote_deployer, script_deployer, etc.
"""

import re
import shlex
from typing import Any, Dict, Optional


def substitute(template: Optional[str], context: Dict[str, Any]) -> Optional[str]:
    """Substitute {{variable}} placeholders with values from context.

    Returns None if template is None, empty string if var not found.
    """
    if not template:
        return template

    def replace_var(match):
        var_name = match.group(1)
        value = context.get(var_name)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{\{(\w+)\}\}", replace_var, template)


def build_sudo_cmd(password: str, cmd: str) -> str:
    """Build a sudo command with proper password escaping.

    Uses printf instead of echo to avoid issues with special characters
    in passwords.
    """
    escaped_password = shlex.quote(password)
    return f"printf '%s\\n' {escaped_password} | sudo -S {cmd}"
