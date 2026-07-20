from google import genai
from google.genai import types
from typing import Dict, Any, List, Union
import json
import logging
import asyncio
from app.core.config import get_settings
from app.core.prompts import GatchaPrompts

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Client specifically for interaction with Google's Gemini API.
    Handles prompt execution, JSON parsing, and retry logic.
    """

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = settings.GEMINI_TEXT_MODEL
        self._lock = asyncio.Lock()

    async def _execute_prompt(
        self, prompt: str, retries: int = 5
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Generic internal method to execute a prompt and return parsed JSON.
        Handles IO blocking, JSON cleaning, and basic retries.
        """
        loop = asyncio.get_running_loop()
        base_delay = 2

        def _generate():
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                # Mode JSON natif : plus fiable qu'un strip manuel de ```json```
                # sur la réponse texte (fragile dès que le modèle change de
                # formatage). Gemini renvoie alors du JSON brut, déjà valide.
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )

        async with self._lock:
            for attempt in range(retries):
                try:
                    # Use executor to avoid blocking the event loop
                    response = await loop.run_in_executor(None, _generate)

                    if not response.text:
                        raise ValueError("Empty response from Gemini")

                    return json.loads(response.text)

                except Exception as e:
                    error_str = str(e)
                    # Retry logic for Rate Limits or server errors
                    if (
                        "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                    ) and attempt < retries - 1:
                        sleep_time = base_delay * (2**attempt)
                        logger.warning(
                            f"Gemini rate limit (attempt {attempt + 1}/{retries}). "
                            f"Retrying in {sleep_time}s..."
                        )
                        await asyncio.sleep(sleep_time)
                        continue

                    if attempt == retries - 1:
                        raise Exception(
                            f"Gemini Execution Error after {retries} attempts: {str(e)}"
                        ) from e

        raise Exception("Gemini Execution failed unexpectedly")

    async def generate_monster_profile(self, user_prompt: str) -> Dict[str, Any]:
        """Generates a structured monster profile."""
        prompt = GatchaPrompts.SINGLE_PROFILE(user_prompt=user_prompt)
        result = await self._execute_prompt(prompt)
        if isinstance(result, list):
            if len(result) > 0:
                return result[0]
            else:
                raise ValueError("Gemini returned an empty list for monster profile")
        return result

    async def generate_batch_brainstorm(self, n: int, user_prompt: str) -> List[Dict[str, Any]]:
        """Brainstorms n monsters without skills."""
        prompt = GatchaPrompts.BATCH_BRAINSTORM(n=n, user_prompt=user_prompt)
        result = await self._execute_prompt(prompt)
        return result if isinstance(result, list) else [result]

    async def generate_batch_skills(self, monsters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Takes a list of monsters and adds skills."""
        monsters_json = json.dumps(monsters, indent=2, ensure_ascii=False)
        prompt = GatchaPrompts.BATCH_SKILLS(monsters_json=monsters_json)
        result = await self._execute_prompt(prompt)
        return result if isinstance(result, list) else [result]
