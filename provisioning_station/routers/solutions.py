"""
Solution management API routes
"""

from typing import List, Optional, Dict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
import markdown

from ..models.api import SolutionSummary, SolutionDetail, SolutionCreate, SolutionUpdate
from ..models.solution import DeviceGroupSection
from ..services.solution_manager import solution_manager
from ..config import settings

router = APIRouter(prefix="/api/solutions", tags=["solutions"])


async def load_device_group_section(
    solution_id: str,
    section: DeviceGroupSection,
    selected_device: Optional[str],
    lang: str,
) -> dict:
    """Load section with template variable replacement"""
    result = {
        "title": section.title_zh if lang == "zh" and section.title_zh else section.title,
    }

    # Select language-specific template file
    template_file = section.description_file_zh if lang == "zh" and section.description_file_zh else section.description_file
    if not template_file:
        return result

    # Load template content (raw markdown, no HTML conversion yet)
    template_content = await solution_manager.load_markdown(
        solution_id, template_file, convert_to_html=False
    )
    if not template_content:
        return result

    # Replace template variables
    if section.variables and selected_device:
        for var_name, device_files in section.variables.items():
            placeholder = "{{" + var_name + "}}"
            if placeholder in template_content:
                # Get content file for this device
                content_file = device_files.get(selected_device)
                if content_file:
                    # Try language-specific version first
                    if lang == "zh":
                        zh_file = content_file.replace('.md', '_zh.md')
                        content = await solution_manager.load_markdown(
                            solution_id, zh_file, convert_to_html=False
                        )
                        if not content:
                            content = await solution_manager.load_markdown(
                                solution_id, content_file, convert_to_html=False
                            )
                    else:
                        content = await solution_manager.load_markdown(
                            solution_id, content_file, convert_to_html=False
                        )
                    template_content = template_content.replace(placeholder, content or '')
                else:
                    # No content for this device, clear the placeholder
                    template_content = template_content.replace(placeholder, '')

    # Convert final content to HTML
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
    result["description"] = md.convert(template_content)

    return result


async def load_preset_section(
    solution_id: str,
    section: DeviceGroupSection,
    selections: dict,
    lang: str,
) -> dict:
    """Load preset section with template variable replacement based on selections.

    For preset sections, variables map to device_group selections.
    E.g. variables: {server_config: {server_high: file1.md, server_low: file2.md}}
    The key in selections that matches determines which file to use.
    """
    result = {
        "title": section.title_zh if lang == "zh" and section.title_zh else section.title,
    }

    # Select language-specific template file
    template_file = section.description_file_zh if lang == "zh" and section.description_file_zh else section.description_file
    if not template_file:
        return result

    # Load template content (raw markdown, no HTML conversion yet)
    template_content = await solution_manager.load_markdown(
        solution_id, template_file, convert_to_html=False
    )
    if not template_content:
        return result

    # Replace template variables using selections
    if section.variables:
        for var_name, device_files in section.variables.items():
            placeholder = "{{" + var_name + "}}"
            if placeholder in template_content:
                # Find which selection value matches a key in device_files
                content_file = None
                for group_id, selected_device in selections.items():
                    if selected_device in device_files:
                        content_file = device_files[selected_device]
                        break

                if content_file:
                    # Try language-specific version first
                    if lang == "zh":
                        zh_file = content_file.replace('.md', '_zh.md')
                        content = await solution_manager.load_markdown(
                            solution_id, zh_file, convert_to_html=False
                        )
                        if not content:
                            content = await solution_manager.load_markdown(
                                solution_id, content_file, convert_to_html=False
                            )
                    else:
                        content = await solution_manager.load_markdown(
                            solution_id, content_file, convert_to_html=False
                        )
                    template_content = template_content.replace(placeholder, content or '')
                else:
                    template_content = template_content.replace(placeholder, '')

    # Convert final content to HTML
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'toc'])
    result["description"] = md.convert(template_content)

    return result


@router.get("/", response_model=List[SolutionSummary])
async def list_solutions(
    category: Optional[str] = None,
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """List all available solutions"""
    solutions = solution_manager.get_all_solutions()

    result = []
    for solution in solutions:
        if category and solution.intro.category != category:
            continue

        # Check file existence for management UI
        base_path = Path(solution.base_path) if solution.base_path else None
        has_description = base_path and (base_path / solution.intro.description_file).exists() if solution.intro.description_file else False
        has_description_zh = base_path and (base_path / solution.intro.description_file_zh).exists() if solution.intro.description_file_zh else False
        has_guide = base_path and (base_path / solution.deployment.guide_file).exists() if solution.deployment.guide_file else False
        has_guide_zh = base_path and (base_path / solution.deployment.guide_file_zh).exists() if solution.deployment.guide_file_zh else False

        summary = SolutionSummary(
            id=solution.id,
            name=solution.name,  # Always return original values for management
            name_zh=solution.name_zh,
            summary=solution.intro.summary,  # Always return original values
            summary_zh=solution.intro.summary_zh,
            category=solution.intro.category,
            tags=solution.intro.tags,
            cover_image=f"/api/solutions/{solution.id}/assets/{solution.intro.cover_image}" if solution.intro.cover_image else None,
            difficulty=solution.intro.stats.difficulty,
            estimated_time=solution.intro.stats.estimated_time,
            deployed_count=solution.intro.stats.deployed_count,
            likes_count=solution.intro.stats.likes_count,
            device_count=len(solution.deployment.devices),
            has_description=has_description,
            has_description_zh=has_description_zh,
            has_guide=has_guide,
            has_guide_zh=has_guide_zh,
        )
        result.append(summary)

    return result


@router.get("/{solution_id}", response_model=SolutionDetail)
async def get_solution(
    solution_id: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get detailed solution information"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Load description from markdown file
    description = None
    description_zh = None
    if solution.intro.description_file:
        description = await solution_manager.load_markdown(solution_id, solution.intro.description_file)
    if solution.intro.description_file_zh:
        description_zh = await solution_manager.load_markdown(solution_id, solution.intro.description_file_zh)

    # Build gallery URLs
    gallery = []
    for item in solution.intro.gallery:
        gallery_item = item.model_dump()
        gallery_item["src"] = f"/api/solutions/{solution_id}/assets/{item.src}"
        if item.thumbnail:
            gallery_item["thumbnail"] = f"/api/solutions/{solution_id}/assets/{item.thumbnail}"
        gallery.append(gallery_item)

    # Build devices summary
    devices = []
    for device in solution.deployment.devices:
        devices.append({
            "id": device.id,
            "name": device.name if lang == "en" else (device.name_zh or device.name),
            "name_zh": device.name_zh,
            "type": device.type,
            "required": device.required,
        })

    # Build required devices with image URLs (legacy)
    required_devices = []
    for device in solution.intro.required_devices:
        dev = device.model_dump()
        if device.image:
            dev["image"] = f"/api/solutions/{solution_id}/assets/{device.image}"
        required_devices.append(dev)

    # Build device catalog by merging global catalog with local overrides
    global_catalog = solution_manager.get_global_device_catalog()
    device_catalog = {}

    # Helper function to resolve device info
    def resolve_device_info(device_id: str, local_device=None) -> dict:
        """Merge global device info with local overrides"""
        result = {}
        # Start with global catalog info
        if device_id in global_catalog:
            result = dict(global_catalog[device_id])
        # Override with local device catalog
        if local_device:
            local_data = local_device.model_dump() if hasattr(local_device, 'model_dump') else dict(local_device)
            for key, value in local_data.items():
                if value is not None:
                    result[key] = value
        # Convert local image paths to URLs
        if result.get("image") and not result["image"].startswith("http"):
            result["image"] = f"/api/solutions/{solution_id}/assets/{result['image']}"
        return result

    # Build local device catalog entries
    for device_id, device in solution.intro.device_catalog.items():
        device_catalog[device_id] = resolve_device_info(device_id, device)

    # Build device groups with resolved device info
    device_groups = []
    for group in solution.intro.device_groups:
        group_data = group.model_dump()
        # Resolve device_ref for quantity type (check local then global)
        if group.type == "quantity" and group.device_ref:
            if group.device_ref in device_catalog:
                group_data["device_info"] = device_catalog[group.device_ref]
            elif group.device_ref in global_catalog:
                group_data["device_info"] = resolve_device_info(group.device_ref, None)
        # Resolve device_ref for options (check local then global)
        if group.options:
            resolved_options = []
            for opt in group.options:
                opt_data = opt.model_dump()
                if opt.device_ref in device_catalog:
                    opt_data["device_info"] = device_catalog[opt.device_ref]
                elif opt.device_ref in global_catalog:
                    opt_data["device_info"] = resolve_device_info(opt.device_ref, None)
                resolved_options.append(opt_data)
            group_data["options"] = resolved_options
        device_groups.append(group_data)

    # Build presets
    presets = []
    for preset in solution.intro.presets:
        presets.append(preset.model_dump())

    # Build partners with logo URLs
    partners = []
    for partner in solution.intro.partners:
        partner_info = {
            "name": partner.name if lang == "en" else (partner.name_zh or partner.name),
            "name_zh": partner.name_zh,
            "logo": f"/api/solutions/{solution_id}/assets/{partner.logo}" if partner.logo else None,
            "regions": partner.regions_en if lang == "en" else partner.regions,
            "contact": partner.contact,
            "website": partner.website,
        }
        partners.append(partner_info)

    return SolutionDetail(
        id=solution.id,
        name=solution.name if lang == "en" else (solution.name_zh or solution.name),
        name_zh=solution.name_zh,
        summary=solution.intro.summary if lang == "en" else (solution.intro.summary_zh or solution.intro.summary),
        summary_zh=solution.intro.summary_zh,
        description=description if lang == "en" else (description_zh or description),
        description_zh=description_zh,
        category=solution.intro.category,
        tags=solution.intro.tags,
        cover_image=f"/api/solutions/{solution_id}/assets/{solution.intro.cover_image}" if solution.intro.cover_image else None,
        gallery=gallery,
        devices=devices,
        required_devices=required_devices,
        device_catalog=device_catalog,
        device_groups=device_groups,
        presets=presets,
        partners=partners,
        stats=solution.intro.stats.model_dump(),
        links={k: v for k, v in solution.intro.links.model_dump().items() if v is not None},
        deployment_order=solution.deployment.order,
        wiki_url=solution.intro.links.wiki,
    )


@router.get("/{solution_id}/deployment")
async def get_deployment_info(
    solution_id: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get deployment page information"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Load deployment guide
    guide = None
    if lang == "zh" and solution.deployment.guide_file_zh:
        guide = await solution_manager.load_markdown(solution_id, solution.deployment.guide_file_zh)
    elif solution.deployment.guide_file:
        guide = await solution_manager.load_markdown(solution_id, solution.deployment.guide_file)

    # Build device sections
    devices = []
    for device in solution.deployment.devices:
        device_info = {
            "id": device.id,
            "name": device.name if lang == "en" else (device.name_zh or device.name),
            "name_zh": device.name_zh,
            "type": device.type,
            "required": device.required,
        }

        # Load device config to get SSH settings, user_inputs, preview settings, etc.
        if device.config_file:
            config = await solution_manager.load_device_config(solution_id, device.config_file)
            if config:
                # Include SSH config for SSH-based deployments
                if config.ssh:
                    device_info["ssh"] = config.ssh.model_dump()
                # Include user_inputs for all device types
                if config.user_inputs:
                    device_info["user_inputs"] = [inp.model_dump() for inp in config.user_inputs]
                # Include preview-specific settings for preview type
                if device.type == "preview":
                    device_info["preview"] = {
                        "user_inputs": [inp.model_dump() for inp in config.user_inputs] if config.user_inputs else [],
                        "video": config.video.model_dump() if config.video else None,
                        "mqtt": config.mqtt.model_dump() if config.mqtt else None,
                        "overlay": config.overlay.model_dump() if config.overlay else None,
                        "display": config.display.model_dump() if config.display else None,
                    }

        if device.section:
            section = device.section
            device_info["section"] = {
                "title": section.title if lang == "en" else (section.title_zh or section.title),
                "title_zh": section.title_zh,
            }

            # Load section description
            desc_file = section.description_file_zh if lang == "zh" else section.description_file
            if desc_file:
                device_info["section"]["description"] = await solution_manager.load_markdown(
                    solution_id, desc_file
                )

            # Load troubleshoot content (shown below deploy button)
            troubleshoot_file = section.troubleshoot_file_zh if lang == "zh" else section.troubleshoot_file
            if troubleshoot_file:
                device_info["section"]["troubleshoot"] = await solution_manager.load_markdown(
                    solution_id, troubleshoot_file
                )

            # Add wiring info
            if section.wiring:
                device_info["section"]["wiring"] = {
                    "image": f"/api/solutions/{solution_id}/assets/{section.wiring.image}" if section.wiring.image else None,
                    "steps": section.wiring.steps_zh if lang == "zh" else section.wiring.steps,
                }

        # Process targets (alternative deployment options within a device step)
        if device.targets:
            targets_data = {}
            for target_id, target in device.targets.items():
                target_info = {
                    "name": target.name if lang == "en" else (target.name_zh or target.name),
                    "name_zh": target.name_zh,
                    "description": target.description if lang == "en" else (target.description_zh or target.description),
                    "description_zh": target.description_zh,
                    "default": target.default,
                    "config_file": target.config_file,
                }
                # Load target section description
                if target.section:
                    target_section = {}
                    desc_file = target.section.description_file_zh if lang == "zh" else target.section.description_file
                    if desc_file:
                        target_section["description"] = await solution_manager.load_markdown(
                            solution_id, desc_file
                        )
                    # Load troubleshoot content
                    troubleshoot_file = target.section.troubleshoot_file_zh if lang == "zh" else target.section.troubleshoot_file
                    if troubleshoot_file:
                        target_section["troubleshoot"] = await solution_manager.load_markdown(
                            solution_id, troubleshoot_file
                        )
                    if target.section.wiring:
                        target_section["wiring"] = {
                            "image": f"/api/solutions/{solution_id}/assets/{target.section.wiring.image}" if target.section.wiring.image else None,
                            "steps": target.section.wiring.steps_zh if lang == "zh" else target.section.wiring.steps,
                        }
                    target_info["section"] = target_section
                targets_data[target_id] = target_info
            device_info["targets"] = targets_data

        devices.append(device_info)

    # Post deployment info
    post_deployment = {}
    if solution.deployment.post_deployment:
        pd = solution.deployment.post_deployment
        if lang == "zh" and pd.success_message_file_zh:
            post_deployment["success_message"] = await solution_manager.load_markdown(
                solution_id, pd.success_message_file_zh
            )
        elif pd.success_message_file:
            post_deployment["success_message"] = await solution_manager.load_markdown(
                solution_id, pd.success_message_file
            )

        post_deployment["next_steps"] = []
        for step in pd.next_steps:
            post_deployment["next_steps"].append({
                "title": step.title if lang == "en" else (step.title_zh or step.title),
                "action": step.action,
                "url": step.url,
            })

    # Build device groups with section content
    device_groups = []
    for group in solution.intro.device_groups:
        group_data = group.model_dump()

        # Process section for this device group
        if group.section:
            # Get selected device (default)
            selected_device = group.default
            if group.type == 'multiple' and group.default_selections:
                selected_device = group.default_selections[0]

            section_data = await load_device_group_section(
                solution_id,
                group.section,
                selected_device,
                lang,
            )
            group_data["section"] = section_data
        else:
            group_data["section"] = None

        device_groups.append(group_data)

    # Build presets with section content
    presets = []
    for preset in solution.intro.presets:
        preset_data = preset.model_dump()
        if preset.section:
            section_data = await load_preset_section(
                solution_id,
                preset.section,
                preset.selections,
                lang,
            )
            preset_data["section"] = section_data
        else:
            preset_data["section"] = None
        presets.append(preset_data)

    return {
        "solution_id": solution_id,
        "guide": guide,
        "selection_mode": solution.deployment.selection_mode,
        "devices": devices,
        "device_groups": device_groups,
        "presets": presets,
        "order": solution.deployment.order,
        "post_deployment": post_deployment,
    }


@router.get("/{solution_id}/assets/{path:path}")
async def get_solution_asset(solution_id: str, path: str):
    """Serve solution asset file"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    asset_path = Path(solution.base_path) / path
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    return FileResponse(asset_path)


@router.get("/{solution_id}/device-group/{group_id}/section")
async def get_device_group_section(
    solution_id: str,
    group_id: str,
    selected_device: str = Query(..., description="Selected device ref"),
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get device group section content with template variable replacement"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Find the device group
    group = None
    for g in solution.intro.device_groups:
        if g.id == group_id:
            group = g
            break

    if not group:
        raise HTTPException(status_code=404, detail="Device group not found")

    if not group.section:
        return {"section": None}

    section_data = await load_device_group_section(
        solution_id,
        group.section,
        selected_device,
        lang,
    )

    return {"section": section_data}


@router.get("/{solution_id}/preset/{preset_id}/section")
async def get_preset_section(
    solution_id: str,
    preset_id: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
):
    """Get preset section content with template variable replacement.

    Selections are passed as query parameters (group_id=device_ref).
    """
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # Find the preset
    preset = None
    for p in solution.intro.presets:
        if p.id == preset_id:
            preset = p
            break

    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    if not preset.section:
        return {"section": None}

    # Use preset's default selections
    selections = dict(preset.selections)

    section_data = await load_preset_section(
        solution_id,
        preset.section,
        selections,
        lang,
    )

    return {"section": section_data}


@router.post("/{solution_id}/like")
async def like_solution(solution_id: str):
    """Increment likes count for a solution"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # In a real app, this would persist to a database
    solution.intro.stats.likes_count += 1
    return {"likes_count": solution.intro.stats.likes_count}


# ============================================
# Solution Management CRUD Routes
# ============================================

@router.post("/", response_model=SolutionSummary)
async def create_solution(data: SolutionCreate):
    """Create a new solution"""
    try:
        solution = await solution_manager.create_solution(data.model_dump())

        return SolutionSummary(
            id=solution.id,
            name=solution.name,
            name_zh=solution.name_zh,
            summary=solution.intro.summary,
            summary_zh=solution.intro.summary_zh,
            category=solution.intro.category,
            tags=solution.intro.tags,
            cover_image=None,
            difficulty=solution.intro.stats.difficulty,
            estimated_time=solution.intro.stats.estimated_time,
            deployed_count=0,
            likes_count=0,
            device_count=0,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create solution: {str(e)}")


@router.put("/{solution_id}", response_model=SolutionSummary)
async def update_solution(solution_id: str, data: SolutionUpdate):
    """Update an existing solution"""
    try:
        # Filter out None values
        update_data = {k: v for k, v in data.model_dump().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        solution = await solution_manager.update_solution(solution_id, update_data)

        return SolutionSummary(
            id=solution.id,
            name=solution.name,
            name_zh=solution.name_zh,
            summary=solution.intro.summary,
            summary_zh=solution.intro.summary_zh,
            category=solution.intro.category,
            tags=solution.intro.tags,
            cover_image=f"/api/solutions/{solution.id}/assets/{solution.intro.cover_image}" if solution.intro.cover_image else None,
            difficulty=solution.intro.stats.difficulty,
            estimated_time=solution.intro.stats.estimated_time,
            deployed_count=solution.intro.stats.deployed_count,
            likes_count=solution.intro.stats.likes_count,
            device_count=len(solution.deployment.devices),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update solution: {str(e)}")


@router.delete("/{solution_id}")
async def delete_solution(
    solution_id: str,
    permanent: bool = Query(False, description="Permanently delete instead of moving to trash")
):
    """Delete a solution (moves to trash by default)"""
    try:
        await solution_manager.delete_solution(solution_id, move_to_trash=not permanent)
        return {"success": True, "message": f"Solution '{solution_id}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete solution: {str(e)}")


@router.post("/{solution_id}/assets")
async def upload_asset(
    solution_id: str,
    file: UploadFile = File(...),
    path: str = Form(..., description="Relative path within solution directory"),
    update_field: Optional[str] = Form(None, description="Optional YAML field to update with this path")
):
    """Upload an asset file to a solution"""
    try:
        # Read file content
        content = await file.read()

        # Max file size: 10MB
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 10MB)")

        # Save the asset
        saved_path = await solution_manager.save_asset(
            solution_id,
            content,
            path,
            update_yaml_field=update_field
        )

        return {
            "success": True,
            "path": saved_path,
            "url": f"/api/solutions/{solution_id}/assets/{saved_path}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload asset: {str(e)}")
