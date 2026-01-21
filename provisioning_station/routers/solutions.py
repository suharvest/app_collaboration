"""
Solution management API routes
"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from ..models.api import SolutionSummary, SolutionDetail
from ..services.solution_manager import solution_manager
from ..config import settings

router = APIRouter(prefix="/api/solutions", tags=["solutions"])


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

        summary = SolutionSummary(
            id=solution.id,
            name=solution.name if lang == "en" else (solution.name_zh or solution.name),
            name_zh=solution.name_zh,
            summary=solution.intro.summary if lang == "en" else (solution.intro.summary_zh or solution.intro.summary),
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

    # Build required devices with image URLs
    required_devices = []
    for device in solution.intro.required_devices:
        dev = device.model_dump()
        if device.image:
            dev["image"] = f"/api/solutions/{solution_id}/assets/{device.image}"
        required_devices.append(dev)

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

            # Add wiring info
            if section.wiring:
                device_info["section"]["wiring"] = {
                    "image": f"/api/solutions/{solution_id}/assets/{section.wiring.image}" if section.wiring.image else None,
                    "steps": section.wiring.steps_zh if lang == "zh" else section.wiring.steps,
                }

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

    return {
        "solution_id": solution_id,
        "guide": guide,
        "selection_mode": solution.deployment.selection_mode,
        "devices": devices,
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


@router.post("/{solution_id}/like")
async def like_solution(solution_id: str):
    """Increment likes count for a solution"""
    solution = solution_manager.get_solution(solution_id)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")

    # In a real app, this would persist to a database
    solution.intro.stats.likes_count += 1
    return {"likes_count": solution.intro.stats.likes_count}
