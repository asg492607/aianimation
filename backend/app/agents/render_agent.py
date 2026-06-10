import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.media import RenderJob, RenderStatus
from app.services.render_service import RenderService
from app.core.logging import get_logger

logger = get_logger(__name__)

class RenderAgent:
    """
    Agent that orchestrates the final Render pipeline.
    It prepares the RenderJob and dispatches it to the RenderService.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.service = RenderService(db)

    async def execute_render(self, project_id: uuid.UUID) -> str:
        # 1. Create RenderJob
        job = RenderJob(
            project_id=project_id,
            status=RenderStatus.QUEUED,
            resolution="1920x1080",
            fps=30,
            format="mp4"
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        logger.info("render_agent_started", project_id=str(project_id), job_id=str(job.id))
        
        # 2. Execute via RenderService (In a real async system, this would be a Celery Task)
        # For the Orchestrator MVP, we will await it directly.
        final_mp4 = await self.service.execute_render_job(job.id)
        
        return final_mp4
