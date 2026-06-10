import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.avatar_engine import AvatarEngine
from app.core.logging import get_logger

logger = get_logger(__name__)

class AvatarAgent:
    """
    Coordinates the creation and application of AI Avatars.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = AvatarEngine()

    async def create_avatar_from_upload(self, user_id: uuid.UUID, image_bytes: bytes) -> dict:
        logger.info("avatar_agent_creating", user_id=str(user_id))
        
        # 1. Process via Engine
        avatar_data = await self.engine.process_photo(image_bytes)
        
        # 2. In a real app, save to Avatar model in DB
        # For MVP, we return the data to be stored in project.meta
        
        return avatar_data
