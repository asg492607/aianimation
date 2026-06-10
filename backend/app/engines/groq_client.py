import json
from typing import Any, Optional

import httpx
from app.core.config import settings
from app.core.exceptions import AIGenerationError
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqClient:
    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL
        self.max_tokens = settings.GROQ_MAX_TOKENS
        self.temperature = settings.GROQ_TEMPERATURE

    async def chat_completion(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "groq_completion",
                    model=self.model,
                    prompt_tokens=data.get("usage", {}).get("prompt_tokens"),
                    completion_tokens=data.get("usage", {}).get("completion_tokens"),
                )
                return data
            except httpx.HTTPStatusError as e:
                logger.error("groq_api_error", status=e.response.status_code, detail=e.response.text)
                raise AIGenerationError(f"Groq API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error("groq_request_error", error=str(e))
                raise AIGenerationError(f"AI generation failed: {str(e)}")

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await self.chat_completion(messages)
        content = response["choices"][0]["message"]["content"]
        try:
            # Strip markdown code fences if present
            if content.strip().startswith("```"):
                content = content.strip().strip("`").strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("groq_json_parse_error", content=content[:500], error=str(e))
            raise AIGenerationError("AI returned invalid JSON response")


groq_client = GroqClient()


class PromptBuilder:
    @staticmethod
    def build_director_prompt(prompt: str) -> tuple[str, str]:
        system = """You are a highly acclaimed Animation Director. Your job is to take a high-level user prompt and plan a multi-engine AI animation project.
        You must decide the visual style, camera style, number of scenes, and target duration.
        Always respond with valid JSON only, no markdown formatting."""

        user = f"""Create an animation direction plan for the following concept:

Concept: {prompt}

Respond ONLY with this JSON structure:
{{
  "animation_style": "3D Cinematic / Anime / Corporate / etc.",
  "camera_style": "Dynamic / Static / Cinematic / etc.",
  "scene_count": 5,
  "target_duration_seconds": 60,
  "mood": "Energetic / Somber / Professional / etc.",
  "director_notes": "Your overall vision for the animation..."
}}"""
        return system, user

    @staticmethod
    def build_character_prompt(script_summary: str) -> tuple[str, str]:
        system = """You are a Character Designer for an animation project.
        Extract the main character from the script summary and design their visual profile to ensure consistency across scenes.
        Always respond with valid JSON only."""

        user = f"""Design the primary character for this script:

Script Summary: {script_summary}

Respond ONLY with this JSON structure:
{{
  "name": "Character Name",
  "hair": "color and style",
  "outfit": "detailed outfit description",
  "age": 25,
  "gender": "male/female/other",
  "avatar_style": "e.g., Business, Casual, Teacher, Doctor",
  "description": "Full physical description"
}}"""
        return system, user

    @staticmethod
    def build_script_prompt(prompt: str, num_scenes: int = 5) -> tuple[str, str]:
        system = """You are a professional animation scriptwriter and creative director. 
        You create detailed, engaging animation scripts with clear visual directions.
        Always respond with valid JSON only, no markdown formatting."""

        user = f"""Create a complete animation script for the following concept:

Concept: {prompt}
Number of scenes: {num_scenes}

Respond ONLY with this JSON structure:
{{
  "title": "Animation title",
  "summary": "2-3 sentence summary",
  "total_duration_seconds": 60,
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Scene title",
      "duration_seconds": 8,
      "narration": "Voiceover text for this scene",
      "visual_description": "Detailed description of what appears on screen",
      "camera_direction": "Camera movement and framing instructions",
      "transition_in": "cut",
      "transition_out": "fade",
      "background_color": "#FFFFFF",
      "key_elements": ["element1", "element2"]
    }}
  ],
  "style_notes": "Overall visual style guidance",
  "mood": "calm/energetic/dramatic/etc",
  "target_audience": "Who this animation is for"
}}"""
        return system, user

    @staticmethod
    def build_storyboard_prompt(scene_description: str, narration: str) -> tuple[str, str]:
        system = """You are a visual storyboard artist. Create detailed descriptions of animation frames.
        Respond with valid JSON only."""

        user = f"""Create a storyboard frame description for this scene:

Visual description: {scene_description}
Narration: {narration}

Respond with JSON:
{{
  "frame_description": "Detailed visual composition",
  "color_palette": ["#hex1", "#hex2"],
  "key_visual_elements": ["element1", "element2"],
  "mood": "description",
  "lighting": "lighting description",
  "text_overlays": []
}}"""
        return system, user

    @staticmethod
    def build_asset_prompt(asset_type: str, description: str) -> tuple[str, str]:
        system = "You are a creative director describing visual assets for animation. Respond in JSON only."

        user = f"""Describe a {asset_type} asset for animation:

Description: {description}

Respond with JSON:
{{
  "asset_name": "descriptive name",
  "detailed_description": "full visual description for image generation",
  "style": "flat/3d/realistic/cartoon",
  "colors": ["#hex1", "#hex2"],
  "dimensions": "1024x1024",
  "background": "transparent/white/none"
}}"""
        return system, user
