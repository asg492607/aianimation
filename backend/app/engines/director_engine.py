from typing import Any
from app.engines.groq_client import groq_client, PromptBuilder
from app.core.exceptions import AIGenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class DirectorEngine:
    """
    DirectorEngine is responsible for high-level project planning:
    style, scene count, duration, and overall vision.
    """
    
    async def generate_project_plan(self, prompt: str) -> dict[str, Any]:
        system_prompt, user_prompt = PromptBuilder.build_director_prompt(prompt)
        
        logger.info("director_engine_planning", prompt=prompt[:100])
        
        try:
            plan = await groq_client.generate_json(system_prompt, user_prompt)
            logger.info("director_engine_success", animation_style=plan.get("animation_style"))
            return plan
        except AIGenerationError as e:
            logger.error("director_engine_failed", error=str(e))
            raise
