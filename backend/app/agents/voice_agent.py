import uuid
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.engines.voice_engine import VoiceEngine
from app.models.media import Voiceover, VoiceoverStatus, VoicoverEngine
from app.models.script import Scene
from app.core.logging import get_logger

logger = get_logger(__name__)

class VoiceAgent:
    """
    Agent that orchestrates the VoiceEngine to generate audio for scenes.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = VoiceEngine()
        # Ensure media directory exists
        os.makedirs("media/voiceovers", exist_ok=True)

    async def generate_voiceovers(self, project_id: uuid.UUID) -> list[Voiceover]:
        # 1. Fetch scenes with narration
        result = await self.db.execute(
            select(Scene).where(Scene.project_id == project_id, Scene.narration != None).order_by(Scene.scene_number)
        )
        scenes = list(result.scalars().all())
        
        voiceovers = []
        for scene in scenes:
            if not scene.narration.strip():
                continue
                
            try:
                # 2. Generate Audio
                audio_data, duration = await self.engine.generate_voiceover(scene.narration)
                
                # 3. Store file locally (MVP)
                file_name = f"{scene.id}.wav"
                file_path = f"media/voiceovers/{file_name}"
                with open(file_path, "wb") as f:
                    f.write(audio_data)
                
                # 4. Create DB Record
                voiceover = Voiceover(
                    project_id=project_id,
                    scene_id=scene.id,
                    text=scene.narration,
                    file_url=file_path,
                    file_key=file_name,
                    duration_seconds=duration,
                    status=VoiceoverStatus.COMPLETED,
                    engine=VoicoverEngine.GENERIC
                )
                self.db.add(voiceover)
                voiceovers.append(voiceover)
                logger.info("voice_agent_generated", scene_id=str(scene.id), duration=duration)
            except Exception as e:
                logger.error("voice_agent_error", scene_id=str(scene.id), error=str(e))
                # Create failed record
                voiceover = Voiceover(
                    project_id=project_id,
                    scene_id=scene.id,
                    text=scene.narration,
                    status=VoiceoverStatus.FAILED,
                    error_message=str(e)
                )
                self.db.add(voiceover)

        await self.db.commit()
        return voiceovers
