from google import genai
from typing import Dict, Any, List, Union
import json
import asyncio
from app.core.config import get_settings
from app.core.prompts import GatchaPrompts


class GeminiClient:
    """
    Client specifically for interaction with Google's Gemini API.
    Handles prompt execution, JSON parsing, and retry logic.
    """

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.0-flash"
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
            )

        async with self._lock:
            for attempt in range(retries):
                try:
                    # Use executor to avoid blocking the event loop
                    response = await loop.run_in_executor(None, _generate)

                    if not response.text:
                        raise ValueError("Empty response from Gemini")

                    # Parse and Clean JSON
                    text_response = response.text
                    clean_json = (
                        text_response.replace("```json", "").replace("```", "").strip()
                    )
                    return json.loads(clean_json)

                except Exception as e:
                    error_str = str(e)
                    # Retry logic for Rate Limits or server errors
                    if (
                        "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                    ) and attempt < retries - 1:
                        sleep_time = base_delay * (2**attempt)
                        logger_msg = f"⚠️ Gemini Rate Limit (Attempt {attempt + 1}/{retries}). Retrying in {sleep_time}s..."
                        print(logger_msg)
                        await asyncio.sleep(sleep_time)
                        continue

                    if attempt == retries - 1:
                        raise Exception(
                            f"Gemini Execution Error after {retries} attempts: {str(e)}"
                        ) from e

        raise Exception("Gemini Execution failed unexpectedly")

    async def generate_monster_profile(self, user_prompt: str) -> Dict[str, Any]:
        """Generates a structured monster profile."""
        prompt = GatchaPrompts.SINGLE_PROFILE.format(user_prompt=user_prompt)
        result = await self._execute_prompt(prompt)
        if isinstance(result, list):
            if len(result) > 0:
                return result[0]
            else:
                raise ValueError("Gemini returned an empty list for monster profile")
        return result

    async def generate_batch_brainstorm(
        self, n: int, user_prompt: str
    ) -> List[Dict[str, Any]]:
        """Brainstorms n monsters without skills."""
        prompt = GatchaPrompts.BATCH_BRAINSTORM.format(n=n, user_prompt=user_prompt)
        result = await self._execute_prompt(prompt)
        return result if isinstance(result, list) else [result]

    async def generate_batch_skills(
        self, monsters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Takes a list of monsters and adds skills."""
        monsters_json = json.dumps(monsters, indent=2, ensure_ascii=False)
        prompt = GatchaPrompts.BATCH_SKILLS.format(monsters_json=monsters_json)
        result = await self._execute_prompt(prompt)
        return result if isinstance(result, list) else [result]
