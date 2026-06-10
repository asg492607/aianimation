import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.models.project import Project, ProjectStatus
from app.repositories.project_repository import ProjectRepository

# Agents
from app.agents.director_agent import DirectorAgent
from app.agents.script_agent import ScriptAgent
from app.agents.scene_agent import SceneAgent
from app.agents.character_agent import CharacterAgent
from app.agents.timeline_agent import TimelineAgent

router = APIRouter()


async def run_ai_generation_pipeline(project_id: uuid.UUID, db: AsyncSession):
    try:
        # 1. Director
        director = DirectorAgent(db)
        plan = await director.plan_project(project_id)
        
        # 2. Script
        script_agent = ScriptAgent(db)
        script_result = await script_agent.write_script(project_id)
        script = script_result["script"]
        
        # 3. Character
        character_agent = CharacterAgent(db)
        character = await character_agent.design_characters(project_id, script.summary or "A story")
        
        # 4. Scenes
        scene_agent = SceneAgent(db)
        scenes = await scene_agent.plan_scenes(project_id, script.id)
        
        # 5. Timeline
        timeline_agent = TimelineAgent(db)
        timeline = await timeline_agent.compile_timeline(project_id)
        
        # Update project status
        repo = ProjectRepository(db)
        await repo.update(project_id, {"status": ProjectStatus.READY})
        
    except Exception as e:
        repo = ProjectRepository(db)
        await repo.update(project_id, {"status": ProjectStatus.FAILED})
        # Log error
        print(f"Pipeline failed: {e}")


@router.post("/{project_id}/generate")
async def generate_project(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    background_tasks.add_task(run_ai_generation_pipeline, project_id, db)
    
    return {"message": "Generation pipeline started", "project_id": str(project_id)}
