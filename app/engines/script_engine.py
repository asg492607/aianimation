from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.groq_client import groq_client, PromptBuilder
from app.repositories.project_repository import ScriptRepository
from app.models.script import ScriptStatus
from app.core.exceptions import AIGenerationError, NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScriptGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.script_repo = ScriptRepository(db)

    async def generate(self, prompt: str, project_id: uuid.UUID, num_scenes: int = 5) -> dict:
        system_prompt, user_prompt = PromptBuilder.build_script_prompt(prompt, num_scenes)

        logger.info("generating_script", project_id=str(project_id), prompt=prompt[:100])

        try:
            ai_response = await groq_client.generate_json(system_prompt, user_prompt)
        except AIGenerationError:
            raise

        validated = ScriptValidator.validate(ai_response)

        # Persist script
        script = await self.script_repo.create({
            "title": validated["title"],
            "summary": validated.get("summary", ""),
            "content": str(validated),
            "status": ScriptStatus.COMPLETED,
            "prompt": prompt,
            "project_id": project_id,
            "raw_ai_response": ai_response,
            "token_count": len(prompt.split()),
        })

        logger.info("script_generated", script_id=str(script.id), title=validated["title"])
        return {"script": script, "parsed": validated}

    async def get_script(self, script_id: uuid.UUID):
        return await self.script_repo.get_or_raise(script_id)


class ScriptValidator:
    REQUIRED_FIELDS = ["title", "scenes"]
    REQUIRED_SCENE_FIELDS = ["scene_number", "narration", "visual_description"]

    @classmethod
    def validate(cls, data: dict) -> dict:
        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                raise AIGenerationError(f"AI response missing required field: {field}")

        if not isinstance(data.get("scenes"), list) or len(data["scenes"]) == 0:
            raise AIGenerationError("AI response must contain at least one scene")

        for i, scene in enumerate(data["scenes"]):
            for field in cls.REQUIRED_SCENE_FIELDS:
                if field not in scene:
                    raise AIGenerationError(f"Scene {i+1} missing required field: {field}")

            # Ensure scene_number is set
            if "scene_number" not in scene:
                scene["scene_number"] = i + 1

            # Default duration
            if "duration_seconds" not in scene:
                scene["duration_seconds"] = 8.0

            # Default transitions
            if "transition_in" not in scene:
                scene["transition_in"] = "cut"
            if "transition_out" not in scene:
                scene["transition_out"] = "cut"

        return data
