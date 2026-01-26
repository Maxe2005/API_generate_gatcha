import uuid
from app.clients.gemini import GeminiClient
from app.clients.banana import BananaClient
from app.schemas.monster import MonsterResponse, MonsterStats

class GatchaService:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.banana_client = BananaClient()

    async def create_monster(self, theme: str, rarity: str = "Common") -> MonsterResponse:
        """
        Orchestrates the creation of a monster: 
        1. Gets text profile from Gemini
        2. Gets image from Banana based on Gemini's visual description
        3. Returns combined object
        """
        
        # Step 1: Generate Profile (IO Bound)
        profile_data = await self.gemini_client.generate_monster_profile(theme, rarity)
        
        # Extract visual description for the image generator
        visual_prompt = profile_data.get("visual_description", theme)
        
        # Step 2: Generate Image (IO Bound)
        # We can optimize this later if needed, but sequential is safer for logic flow
        image_url = await self.banana_client.generate_pixel_art(visual_prompt)
        
        # Step 3: Construct Response
        return MonsterResponse(
            name=profile_data["name"],
            element=profile_data["element"],
            rarity=profile_data["rarity"],
            lore=profile_data["lore"],
            stats=MonsterStats(**profile_data["stats"]),
            image_url=image_url,
            generation_id=str(uuid.uuid4())
        )
