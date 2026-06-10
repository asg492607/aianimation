from typing import List
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.groq_client import groq_client, PromptBuilder
from app.repositories.project_repository import SceneRepository, StoryboardRepository, ScriptRepository
from app.models.script import SceneTransition
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScenePlanner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scene_repo = SceneRepository(db)
        self.script_repo = ScriptRepository(db)

    async def generate_scenes_from_script(self, project_id: uuid.UUID, script_id: uuid.UUID) -> List:
        script = await self.script_repo.get_or_raise(script_id)
        raw = script.raw_ai_response or {}
        scenes_data = raw.get("scenes", [])

        if not scenes_data:
            raise ValueError("Script has no scene data")

        created_scenes = []
        for scene_data in scenes_data:
            transition_in = scene_data.get("transition_in", "cut")
            transition_out = scene_data.get("transition_out", "cut")

            # Normalize transition values
            try:
                t_in = SceneTransition(transition_in.lower())
            except ValueError:
                t_in = SceneTransition.CUT
            try:
                t_out = SceneTransition(transition_out.lower())
            except ValueError:
                t_out = SceneTransition.CUT

            scene = await self.scene_repo.create({
                "scene_number": scene_data["scene_number"],
                "title": scene_data.get("title"),
                "duration_seconds": float(scene_data.get("duration_seconds", 8.0)),
                "narration": scene_data.get("narration"),
                "visual_description": scene_data.get("visual_description"),
                "camera_direction": scene_data.get("camera_direction"),
                "transition_in": t_in,
                "transition_out": t_out,
                "background_color": scene_data.get("background_color"),
                "meta": {"key_elements": scene_data.get("key_elements", [])},
                "project_id": project_id,
                "script_id": script_id,
            })
            created_scenes.append(scene)
            logger.info("scene_created", scene_id=str(scene.id), number=scene.scene_number)

        return created_scenes


class StoryboardGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storyboard_repo = StoryboardRepository(db)

    async def generate_for_scene(self, scene_id: uuid.UUID, visual_description: str, narration: str) -> dict:
        system_prompt, user_prompt = PromptBuilder.build_storyboard_prompt(visual_description, narration)

        storyboard_data = await groq_client.generate_json(system_prompt, user_prompt)

        storyboard = await self.storyboard_repo.create({
            "scene_id": scene_id,
            "description": storyboard_data.get("frame_description", ""),
            "notes": str(storyboard_data),
            "is_approved": False,
        })

        logger.info("storyboard_created", storyboard_id=str(storyboard.id), scene_id=str(scene_id))
        return {"storyboard": storyboard, "data": storyboard_data}


class TimelineGenerator:
    @staticmethod
    def generate_timeline(scenes: list) -> dict:
        timeline = []
        current_time = 0.0

        for scene in scenes:
            entry = {
                "scene_id": str(scene.id),
                "scene_number": scene.scene_number,
                "start_time": current_time,
                "end_time": current_time + scene.duration_seconds,
                "duration": scene.duration_seconds,
                "transition_in": scene.transition_in.value if scene.transition_in else "cut",
                "transition_out": scene.transition_out.value if scene.transition_out else "cut",
                "narration": scene.narration,
            }
            timeline.append(entry)
            current_time += scene.duration_seconds

        return {
            "total_duration": current_time,
            "scene_count": len(scenes),
            "timeline": timeline,
        }
