import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import ProjectStatus
from app.models.system import AIJob, JobStatus
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
    Executes the entire generation pipeline DAG and tracks progress in AIJob.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)

    async def _log_job(self, project_id: uuid.UUID, agent_name: str, status: JobStatus) -> AIJob:
        job = AIJob(
            project_id=project_id,
            job_type=f"{agent_name}_execution",
            status=status,
            agent_id=agent_name
        )
        self.db.add(job)
        await self.db.commit()
        return job

    async def run_pipeline(self, project_id: uuid.UUID) -> None:
        try:
            logger.info("orchestrator_started", project_id=str(project_id))
            
            # 1. Director
            await self._log_job(project_id, "DirectorAgent", JobStatus.RUNNING)
            plan = await DirectorAgent(self.db).plan_project(project_id)
            
            # 2. Script
            await self._log_job(project_id, "ScriptAgent", JobStatus.RUNNING)
            script_result = await ScriptAgent(self.db).write_script(project_id)
            script = script_result["script"]
            
            # 3. Character
            await self._log_job(project_id, "CharacterAgent", JobStatus.RUNNING)
            await CharacterAgent(self.db).design_characters(project_id, script.summary or "A story")
            
            # 4. Scene
            await self._log_job(project_id, "SceneAgent", JobStatus.RUNNING)
            scenes = await SceneAgent(self.db).plan_scenes(project_id, script.id)
            
            # 5. Storyboard
            await self._log_job(project_id, "StoryboardAgent", JobStatus.RUNNING)
            await StoryboardAgent(self.db).create_storyboards(project_id)
            
            # 6. Camera
            await self._log_job(project_id, "CameraAgent", JobStatus.RUNNING)
            await CameraAgent(self.db).plan_camera(project_id)
            
            # 7. Asset
            await self._log_job(project_id, "AssetAgent", JobStatus.RUNNING)
            await AssetAgent(self.db).generate_assets(project_id)
            
            # 8. Voice
            await self._log_job(project_id, "VoiceAgent", JobStatus.RUNNING)
            await VoiceAgent(self.db).generate_voiceovers(project_id)
            
            # 9. Music
            await self._log_job(project_id, "MusicAgent", JobStatus.RUNNING)
            duration = float(plan.get("target_duration_seconds", 60.0))
            mood = plan.get("mood", "cinematic")
            await MusicAgent(self.db).generate_music(project_id, duration, mood)
            
            # 10. Timeline
            await self._log_job(project_id, "TimelineAgent", JobStatus.RUNNING)
            await TimelineAgent(self.db).compile_timeline(project_id)
            
            # 11. Render
            await self._log_job(project_id, "RenderAgent", JobStatus.RUNNING)
            await self.project_repo.update(project_id, {"status": ProjectStatus.RENDERING})
            mp4_path = await RenderAgent(self.db).execute_render(project_id)
            
            # 12. Export
            await self._log_job(project_id, "ExportAgent", JobStatus.RUNNING)
            await ExportAgent(self.db).export_project(project_id, mp4_path)
            
            # Finish
            await self._log_job(project_id, "Orchestrator", JobStatus.COMPLETED)
            await self.project_repo.update(project_id, {"status": ProjectStatus.COMPLETED})
            logger.info("orchestrator_completed", project_id=str(project_id))

        except Exception as e:
            await self._log_job(project_id, "Orchestrator", JobStatus.FAILED)
            await self.project_repo.update(project_id, {"status": ProjectStatus.FAILED})
            logger.error("orchestrator_failed", project_id=str(project_id), error=str(e))
