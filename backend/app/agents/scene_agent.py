import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.scene_engine import ScenePlanner
from app.core.logging import get_logger

logger = get_logger(__name__)


class SceneAgent:
    """
    Agent that orchestrates the ScenePlanner to break down a generated script into DB scenes.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = ScenePlanner(db)

    async def plan_scenes(self, project_id: uuid.UUID, script_id: uuid.UUID) -> list:
        scenes = await self.engine.generate_scenes_from_script(project_id, script_id)
        
        logger.info("scene_agent_completed", project_id=str(project_id), num_scenes=len(scenes))
        return scenes
