import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.session import get_projects

router = APIRouter()


class GenerateRequest(BaseModel):
    title: str
    prompt: str
    meta: Optional[dict] = None


@router.post("/{project_id}/generate")
async def generate_project(project_id: uuid.UUID, request: GenerateRequest):
    projects = get_projects()
    pid = str(project_id)
    projects[pid] = {
        "id": pid,
        "title": request.title,
        "prompt": request.prompt,
        "meta": request.meta,
        "status": "queued",
    }
    return {"message": "Generation pipeline dispatched", "project_id": pid}


@router.post("/{project_id}/scenes/{scene_id}/regenerate-assets")
async def regenerate_scene_assets(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Dispatched asset regeneration for scene {scene_id}"}


@router.post("/{project_id}/scenes/{scene_id}/regenerate-voice")
async def regenerate_scene_voice(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Dispatched voice regeneration for scene {scene_id}"}


class TimelineUpdate(BaseModel):
    ordered_scene_ids: list[str]


@router.put("/{project_id}/timeline")
async def update_timeline(project_id: uuid.UUID, update: TimelineUpdate):
    return {"message": "Timeline updated successfully", "new_order": update.ordered_scene_ids}


@router.delete("/{project_id}/scenes/{scene_id}")
async def delete_scene(project_id: uuid.UUID, scene_id: uuid.UUID):
    return {"message": f"Scene {scene_id} deleted"}
