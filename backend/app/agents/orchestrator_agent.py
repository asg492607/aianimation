import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import ProjectStatus
from app.repositories.project_repository import ProjectRepository
from app.core.logging import get_logger

# Agents
from app.agents.director_agent import DirectorAgent
from app.agents.script_agent import ScriptAgent
from app.agents.character_agent import CharacterAgent
from app.agents.storyboard_agent import StoryboardAgent
from app.agents.scene_agent import SceneAgent
from app.agents.camera_agent import CameraAgent
from app.agents.asset_agent import AssetAgent
from app.agents.voice_agent import VoiceAgent
from app.agents.music_agent import MusicAgent
from app.agents.timeline_agent import TimelineAgent
from app.agents.render_agent import RenderAgent
from app.agents.export_agent import ExportAgent

logger = get_logger(__name__)

class OrchestratorAgent:
    """
    The master brain.
    Executes the entire generation pipeline DAG:
    Director -> Script -> Character -> Scene -> Storyboard -> Camera -> Asset -> Voice -> Music -> Timeline -> Render -> Export
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)

    async def run_pipeline(self, project_id: uuid.UUID) -> None:
        try:
            logger.info("orchestrator_started", project_id=str(project_id))
            
            # 1. Director
            plan = await DirectorAgent(self.db).plan_project(project_id)
            
            # 2. Script
            script_result = await ScriptAgent(self.db).write_script(project_id)
            script = script_result["script"]
            
            # 3. Character
            await CharacterAgent(self.db).design_characters(project_id, script.summary or "A story")
            
            # 4. Scene
            scenes = await SceneAgent(self.db).plan_scenes(project_id, script.id)
            
            # 5. Storyboard
            await StoryboardAgent(self.db).create_storyboards(project_id)
            
            # 6. Camera
            await CameraAgent(self.db).plan_camera(project_id)
            
            # 7. Asset
            await AssetAgent(self.db).generate_assets(project_id)
            
            # 8. Voice
            await VoiceAgent(self.db).generate_voiceovers(project_id)
            
            # 9. Music
            duration = float(plan.get("target_duration_seconds", 60.0))
            mood = plan.get("mood", "cinematic")
            await MusicAgent(self.db).generate_music(project_id, duration, mood)
            
            # 10. Timeline
            await TimelineAgent(self.db).compile_timeline(project_id)
            
            # 11. Render
            # Updates status to RENDERING implicitly via RenderService
            await self.project_repo.update(project_id, {"status": ProjectStatus.RENDERING})
            mp4_path = await RenderAgent(self.db).execute_render(project_id)
            
            # 12. Export
            await ExportAgent(self.db).export_project(project_id, mp4_path)
            
            # Finish
            await self.project_repo.update(project_id, {"status": ProjectStatus.COMPLETED})
            logger.info("orchestrator_completed", project_id=str(project_id))

        except Exception as e:
            await self.project_repo.update(project_id, {"status": ProjectStatus.FAILED})
            logger.error("orchestrator_failed", project_id=str(project_id), error=str(e))
