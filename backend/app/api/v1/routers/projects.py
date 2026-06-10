import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.models.project import Project, ProjectStatus
from app.repositories.project_repository import ProjectRepository

# Agents
from app.agents.orchestrator_agent import OrchestratorAgent

router = APIRouter()


async def run_ai_generation_pipeline(project_id: uuid.UUID, db: AsyncSession):
    orchestrator = OrchestratorAgent(db)
    await orchestrator.run_pipeline(project_id)


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
