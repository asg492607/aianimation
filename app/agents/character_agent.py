import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.engines.character_engine import CharacterEngine
from app.models.advanced import Character
from app.models.project import Project
from app.core.logging import get_logger

logger = get_logger(__name__)


class CharacterAgent:
    """
    Agent that orchestrates the CharacterEngine and saves Character DB records.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = CharacterEngine()

    async def design_characters(self, project_id: uuid.UUID, script_summary: str) -> Character:
        # Check if character already exists
        result = await self.db.execute(
            select(Character).where(Character.project_id == project_id)
        )
        existing = result.scalars().first()
        if existing:
            return existing
            
        profile_data = await self.engine.extract_character_profile(script_summary)
        
        character = Character(
            project_id=project_id,
            name=profile_data.get("name", "Unknown"),
            hair=profile_data.get("hair"),
            outfit=profile_data.get("outfit"),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            avatar_style=profile_data.get("avatar_style"),
            description=profile_data.get("description")
        )
        
        self.db.add(character)
        await self.db.commit()
        await self.db.refresh(character)
        
        logger.info("character_agent_completed", project_id=str(project_id), character_id=str(character.id))
        return character
