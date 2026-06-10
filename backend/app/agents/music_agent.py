import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.advanced import MusicTrack
from app.engines.music_engine import MusicEngine
from app.core.logging import get_logger

logger = get_logger(__name__)

class MusicAgent:
    """
    Plans background music for the TimelineAgent.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_music(self, project_id: uuid.UUID, duration: float, mood: str) -> MusicTrack:
        file_name = f"{project_id}_{mood}.mp3"
        file_path = f"media/music/{file_name}"
        
        # Fetch the track
        engine = MusicEngine()
        await engine.fetch_track(mood, duration, file_path)

        track = MusicTrack(
            project_id=project_id,
            title=f"Background Theme ({mood})",
            file_url=file_path,
            file_key=file_name,
            genre="cinematic",
            duration_seconds=duration,
            mood=mood
        )
        self.db.add(track)
        await self.db.commit()
        
        logger.info("music_agent_completed", project_id=str(project_id), duration=duration)
        return track
