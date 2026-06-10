from typing import Any
from app.engines.groq_client import groq_client, PromptBuilder
from app.core.exceptions import AIGenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class CharacterEngine:
    """
    CharacterEngine is responsible for maintaining character consistency.
    It extracts the primary character profile from a script or story summary.
    """
    
    async def extract_character_profile(self, script_summary: str) -> dict[str, Any]:
        system_prompt, user_prompt = PromptBuilder.build_character_prompt(script_summary)
        
        logger.info("character_engine_extracting")
        
        try:
            profile = await groq_client.generate_json(system_prompt, user_prompt)
            logger.info("character_engine_success", character_name=profile.get("name"))
            return profile
        except AIGenerationError as e:
            logger.error("character_engine_failed", error=str(e))
            raise
