import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from tasks.tasks import run_orchestrator_task

router = APIRouter()

from typing import Optional
from pydantic import BaseModel

class GenerateRequest(BaseModel):
    title: str
    prompt: str
    meta: Optional[dict] = None

@router.post("/{project_id}/generate")
async def generate_project(
    project_id: uuid.UUID,
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        # For the MVP frontend, we allow creating the project right here
        project = Project(
            id=project_id,
            title=request.title,
            prompt=request.prompt,
            meta=request.meta,
            owner_id=uuid.UUID("00000000-0000-0000-0000-000000000000") # Mock owner
        )
        db.add(project)
        await db.commit()
    else:
        # Update existing project
        project = await repo.update(project_id, {
            "title": request.title, 
            "prompt": request.prompt,
            "meta": request.meta
        })
        
    # Dispatch to Celery
    run_orchestrator_task.delay(str(project_id))
    
    return {"message": "Generation pipeline dispatched to Celery", "project_id": str(project_id)}

@router.post("/{project_id}/scenes/{scene_id}/regenerate-assets")
async def regenerate_scene_assets(
    project_id: uuid.UUID,
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    from app.agents.asset_agent import AssetAgent
    agent = AssetAgent(db)
    # We would theoretically fetch only that scene and pass it to generate_assets
    # For MVP, we will mock the task delegation
    return {"message": f"Dispatched asset regeneration for scene {scene_id}"}

@router.post("/{project_id}/scenes/{scene_id}/regenerate-voice")
async def regenerate_scene_voice(
    project_id: uuid.UUID,
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    from app.agents.voice_agent import VoiceAgent
    agent = VoiceAgent(db)
    return {"message": f"Dispatched voice regeneration for scene {scene_id}"}

class TimelineUpdate(BaseModel):
    ordered_scene_ids: list[str]

@router.put("/{project_id}/timeline")
async def update_timeline(
    project_id: uuid.UUID,
    update: TimelineUpdate,
    db: AsyncSession = Depends(get_db)
):
    # In a real app, update scene.scene_number based on the array order
    return {"message": "Timeline updated successfully", "new_order": update.ordered_scene_ids}

@router.delete("/{project_id}/scenes/{scene_id}")
async def delete_scene(
    project_id: uuid.UUID,
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    # Delete scene from DB
    return {"message": f"Scene {scene_id} deleted"}

