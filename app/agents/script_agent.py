import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.engines.script_engine import ScriptGenerator
from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptAgent:
    """
    Agent that orchestrates the ScriptGenerator based on Director's plan.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = ScriptGenerator(db)
        self.project_repo = ProjectRepository(db)

    async def write_script(self, project_id: uuid.UUID) -> dict:
        project = await self.project_repo.get_or_raise(project_id)
        
        # Get director plan from meta
        meta = project.meta or {}
        plan = meta.get("director_plan", {})
        num_scenes = plan.get("scene_count", 5)
        
        # Create an augmented prompt for the script engine based on the director plan
        director_prompt = f"Original Prompt: {project.prompt}\n"
        director_prompt += f"Animation Style: {plan.get('animation_style', 'Standard')}\n"
        director_prompt += f"Camera Style: {plan.get('camera_style', 'Standard')}\n"
        director_prompt += f"Mood: {plan.get('mood', 'Standard')}\n"
        director_prompt += f"Director Notes: {plan.get('director_notes', 'None')}\n"
        
        result = await self.engine.generate(director_prompt, project_id, num_scenes)
        
        logger.info("script_agent_completed", project_id=str(project_id))
        return result
