import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.script import Scene, Storyboard
from app.engines.scene_engine import StoryboardGenerator
from app.core.logging import get_logger

logger = get_logger(__name__)

class StoryboardAgent:
    """
    Creates detailed visual frame descriptions for the AssetAgent.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.generator = StoryboardGenerator(db)

    async def create_storyboards(self, project_id: uuid.UUID) -> list[Storyboard]:
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id)
        )
        scenes = list(result.scalars().all())
        
        storyboards = []
        for scene in scenes:
            # Generate storyboard via LLM
            res = await self.generator.generate_for_scene(
                scene_id=scene.id,
                visual_description=scene.visual_description or "",
                narration=scene.narration or ""
            )
            storyboards.append(res["storyboard"])
            
        logger.info("storyboard_agent_completed", project_id=str(project_id))
        return storyboards
