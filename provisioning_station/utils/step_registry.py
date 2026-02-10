"""
Step registry for automatic deployment step generation.

Each deployer type has a fixed sequence of steps. Instead of declaring them
manually in every YAML file, this registry generates them from the device type.

Conditional steps (actions_before / actions_after) are only included when the
device config actually defines those action hooks.
"""

from typing import Dict, List

from ..models.device import DeploymentStep, DeviceConfig

# ---------------------------------------------------------------------------
# Step templates per deployer type.
#
# "_condition" marks steps that are only included when a condition is met:
#   "actions.before" → config.actions.before is non-empty
#   "actions.after"  → config.actions.after  is non-empty
# ---------------------------------------------------------------------------

DEPLOYER_STEPS: Dict[str, List[dict]] = {
    # ----- Docker (local) --------------------------------------------------
    "docker_local": [
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {
            "id": "pull_images",
            "name": "Pull Docker Images",
            "name_zh": "拉取 Docker 镜像",
        },
        {
            "id": "create_volumes",
            "name": "Create Data Volumes",
            "name_zh": "创建数据卷",
        },
        {"id": "start_services", "name": "Start Services", "name_zh": "启动服务"},
        {"id": "health_check", "name": "Health Check", "name_zh": "健康检查"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- Docker (remote via SSH) -----------------------------------------
    "docker_remote": [
        {"id": "connect", "name": "Connect", "name_zh": "连接设备"},
        {"id": "check_os", "name": "Check OS", "name_zh": "检查系统"},
        {"id": "check_docker", "name": "Check Docker", "name_zh": "检查 Docker"},
        {"id": "prepare", "name": "Prepare Environment", "name_zh": "准备环境"},
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {"id": "upload", "name": "Upload Files", "name_zh": "上传文件"},
        {"id": "pull_images", "name": "Pull Docker Images", "name_zh": "拉取镜像"},
        {"id": "start_services", "name": "Start Services", "name_zh": "启动服务"},
        {"id": "health_check", "name": "Health Check", "name_zh": "健康检查"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- ESP32 USB flashing ----------------------------------------------
    "esp32_usb": [
        {"id": "detect", "name": "Detect Device", "name_zh": "检测设备"},
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {"id": "erase", "name": "Erase Flash", "name_zh": "擦除闪存"},
        {"id": "flash", "name": "Flash Firmware", "name_zh": "烧录固件"},
        {"id": "verify", "name": "Verify", "name_zh": "验证"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- Himax USB flashing ----------------------------------------------
    "himax_usb": [
        {"id": "detect", "name": "Detect Device", "name_zh": "检测设备"},
        {"id": "prepare", "name": "Prepare", "name_zh": "准备"},
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {"id": "flash", "name": "Flash Firmware", "name_zh": "烧录固件"},
        {"id": "verify", "name": "Verify", "name_zh": "验证"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- reCamera C++ deployment -----------------------------------------
    "recamera_cpp": [
        {"id": "connect", "name": "Connect", "name_zh": "连接设备"},
        {"id": "precheck", "name": "Pre-check", "name_zh": "预检查"},
        {"id": "prepare", "name": "Stop Conflicts", "name_zh": "停止冲突服务"},
        {"id": "transfer", "name": "Transfer Files", "name_zh": "传输文件"},
        {"id": "install", "name": "Install Package", "name_zh": "安装软件包"},
        {"id": "models", "name": "Deploy Models", "name_zh": "部署模型"},
        {"id": "configure", "name": "Configure", "name_zh": "配置服务"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
        {"id": "start", "name": "Start Service", "name_zh": "启动服务"},
        {"id": "verify", "name": "Verify", "name_zh": "验证"},
    ],
    # ----- reCamera Node-RED deployment ------------------------------------
    "recamera_nodered": [
        {"id": "prepare", "name": "Prepare", "name_zh": "准备环境"},
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {"id": "load_flow", "name": "Load Flow", "name_zh": "加载流程"},
        {"id": "configure", "name": "Configure", "name_zh": "配置"},
        {"id": "connect", "name": "Connect", "name_zh": "连接"},
        {"id": "deploy", "name": "Deploy", "name_zh": "部署"},
        {"id": "verify", "name": "Verify", "name_zh": "验证"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- Script deployment -----------------------------------------------
    "script": [
        {"id": "validate", "name": "Validate", "name_zh": "验证环境"},
        {
            "id": "actions_before",
            "name": "Custom Setup",
            "name_zh": "自定义准备",
            "_condition": "actions.before",
        },
        {"id": "setup", "name": "Setup", "name_zh": "安装"},
        {"id": "configure", "name": "Configure", "name_zh": "配置"},
        {"id": "start", "name": "Start", "name_zh": "启动"},
        {"id": "health_check", "name": "Health Check", "name_zh": "健康检查"},
        {
            "id": "actions_after",
            "name": "Custom Config",
            "name_zh": "自定义配置",
            "_condition": "actions.after",
        },
    ],
    # ----- Preview (no real deployment) ------------------------------------
    "preview": [
        {"id": "preview_setup", "name": "Preview Setup", "name_zh": "预览设置"},
    ],
}


def get_steps_for_config(config: DeviceConfig) -> List[DeploymentStep]:
    """Generate deployment steps from device type and actions config.

    Returns an empty list for types not in the registry (e.g. ``manual``),
    meaning the YAML must declare steps explicitly.
    """
    template = DEPLOYER_STEPS.get(config.type)
    if template is None:
        return []

    steps: List[DeploymentStep] = []
    for entry in template:
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
