import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.media import Export, ExportStatus, ExportFormat
from app.core.logging import get_logger

logger = get_logger(__name__)

class ExportAgent:
    """
    Prepares the final MP4 for different RenderProfiles (e.g., cropping).
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_project(self, project_id: uuid.UUID, mp4_url: str) -> Export:
        # MVP: Just register the generated MP4 as a completed export.
        export_job = Export(
            project_id=project_id,
            format=ExportFormat.MP4,
            status=ExportStatus.COMPLETED,
            file_url=mp4_url
        )
        self.db.add(export_job)
        await self.db.commit()
        
        logger.info("export_agent_completed", project_id=str(project_id))
        return export_job
