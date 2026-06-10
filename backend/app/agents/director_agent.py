import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.director_engine import DirectorEngine
from app.repositories.project_repository import ProjectRepository
from app.models.project import ProjectStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class DirectorAgent:
    """
    Agent that orchestrates the DirectorEngine and updates the Project state.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = DirectorEngine()
        self.project_repo = ProjectRepository(db)

    async def plan_project(self, project_id: uuid.UUID) -> dict:
        project = await self.project_repo.get_or_raise(project_id)
        
        # 1. Update status
        project = await self.project_repo.update(project_id, {"status": ProjectStatus.GENERATING})
        
        # 2. Run Engine
        style = project.meta.get("requested_style", "3D Cinematic") if project.meta else "3D Cinematic"
        plan_data = await self.engine.generate_project_plan(project.prompt, style)
        
        # 3. Save Plan to Project Meta
        current_meta = project.meta or {}
        current_meta["director_plan"] = plan_data
        
        project = await self.project_repo.update(
            project_id, 
            {
                "meta": current_meta,
                "duration_seconds": float(plan_data.get("target_duration_seconds", 60.0))
            }
        )
        
        logger.info("director_agent_completed", project_id=str(project_id))
        return plan_data
