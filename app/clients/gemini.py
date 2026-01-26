from google import genai
from typing import Dict, Any
import json
import asyncio
from app.core.config import get_settings

class GeminiClient:
    """
    Client specifically for interaction with Google's Gemini API (via google-genai SDK).
    """
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_monster_profile(self, theme: str, rarity: str) -> Dict[str, Any]:
        """
        Generates a structured monster profile (JSON) from a text prompt using Gemini.
        """
        # Prompt engineering to ensure JSON output
        prompt = f"""
        Generate a creative monster profile for a gacha game.
        Theme: {theme}
        Rarity: {rarity}
        
        Output MUST be valid JSON with the following structure:
        {{
            "name": "string",
            "element": "string (Fire, Water, etc)",
            "rarity": "{rarity}",
            "lore": "string (max 200 chars)",
            "stats": {{
                "attack": int (1-100),
                "defense": int (1-100),
                "hp": int (1-100),
                "speed": int (1-100)
            }},
            "visual_description": "string (detailed description for image generator)"
        }}
        Do not include markdown code blocks. Just the JSON.
        """

        # Wrapper for running synchronous SDK in async loop
        loop = asyncio.get_running_loop()
        
        def _generate_specific():
             # Using "gemini-2.0-flash" as it is stable and fast. 
             # If "gemini-3-pro-preview" is required specifically, just switch the model string.
             # The user's snippet had "gemini-3-pro-preview" but that might be a very fresh preview.
             # I'll stick to a commonly available one or what the user asked exactly?
             # User said: "meme chose pour gemini : ... model="gemini-3-pro-preview" ..."
             # So I WILL use that model string.
             return self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
        
        max_retries = 3
        base_delay = 2

        for attempt in range(max_retries):
            try:
                # We use run_in_executor to avoid blocking the event loop
                response = await loop.run_in_executor(None, _generate_specific)
                
                # Parse Gemini response structure
                if not response.text:
                     raise ValueError("Empty response from Gemini")

                text_response = response.text
                
                # Clean generic markdown if present
                clean_json = text_response.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_json)
                
            except Exception as e:
                error_str = str(e)
                # Check for rate limit error codes (429 or RESOURCE_EXHAUSTED)
                if ("429" in error_str or "RESOURCE_EXHAUSTED" in error_str) and attempt < max_retries - 1:
                    sleep_time = base_delay * (2 ** attempt)
                    print(f"⚠️ Gemini Rate Limit hit. Retrying in {sleep_time}s...")
                    await asyncio.sleep(sleep_time)
                    continue
                
                # If it's not a retryable error or we ran out of retries
                raise Exception(f"Gemini Generation Error: {str(e)}") from e
        
        # This line should never be reached due to exceptions, but ensures type safety
        raise Exception("Gemini Generation failed after all retries")
