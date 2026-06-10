import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from tasks.tasks import run_orchestrator_task

router = APIRouter()

@router.post("/{project_id}/generate")
async def generate_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Dispatch to Celery
    run_orchestrator_task.delay(str(project_id))
    
    return {"message": "Generation pipeline dispatched to Celery", "project_id": str(project_id)}
