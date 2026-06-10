import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.engines.timeline_engine import TimelineEngine
from app.models.advanced import Timeline
from app.models.script import Scene
from app.core.logging import get_logger

logger = get_logger(__name__)


class TimelineAgent:
    """
    Agent that generates the Timeline DB records from existing scenes.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = TimelineEngine()

    async def compile_timeline(self, project_id: uuid.UUID) -> list[Timeline]:
        # 1. Clear existing timeline
        await self.db.execute(
            Timeline.__table__.delete().where(Timeline.project_id == project_id)
        )
        
        # 2. Fetch scenes
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id).order_by(Scene.scene_number)
        )
        scenes = list(result.scalars().all())
        
        if not scenes:
            raise ValueError("No scenes found for project")
            
        # 3. Generate Timeline
        timeline_entries = self.engine.generate_timeline_from_scenes(project_id, scenes)
        
        self.db.add_all(timeline_entries)
        await self.db.commit()
        
        logger.info("timeline_agent_completed", project_id=str(project_id), entries_count=len(timeline_entries))
        return timeline_entries
