import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.advanced import CameraMovement
from app.models.script import Scene
from app.core.logging import get_logger

logger = get_logger(__name__)

class CameraAgent:
    """
    Analyzes scenes and assigns camera movements.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def plan_camera(self, project_id: uuid.UUID) -> list[CameraMovement]:
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id)
        )
        scenes = list(result.scalars().all())
        
        movements = []
        for scene in scenes:
            # MVP: Parse the 'camera_direction' string if it exists
            style = scene.camera_direction or "Static"
            cm = CameraMovement(
                scene_id=scene.id,
                style=style,
                parameters={"zoom_factor": 1.1} if "zoom" in style.lower() else {}
            )
            self.db.add(cm)
            movements.append(cm)
            
        await self.db.commit()
        logger.info("camera_agent_completed", project_id=str(project_id))
        return movements
