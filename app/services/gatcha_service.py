import uuid
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from app.clients.gemini import GeminiClient
from app.clients.banana import BananaClient
from app.schemas.monster import MonsterResponse
from app.utils.file_manager import FileManager
from app.services.validation_service import MonsterValidationService
import logging

logger = logging.getLogger(__name__)


class GatchaService:
    def __init__(self):
        self.gemini_client = GeminiClient()
        self.banana_client = BananaClient()
        self.file_manager = FileManager()
        self.validation_service = MonsterValidationService()

    def _get_filename_base(self, monster_data: Dict[str, Any]) -> str:
        """Build a safe filename base from monster name."""
        monster_name = monster_data.get("nom", "unknown_monster")
        filename_base = self.file_manager.sanitize_filename(monster_name)
        if not filename_base:
            filename_base = f"monster_{uuid.uuid4().hex[:8]}"
        return filename_base

    async def _generate_image(
        self, monster_data: Dict[str, Any], fallback_prompt: str, filename_base: str
    ) -> str:
        """Generate image for a monster, safe-failing on errors."""
        visual_prompt = monster_data.get("description_visuelle", fallback_prompt)
        try:
            return await self.banana_client.generate_pixel_art(
                visual_prompt, filename_base
            )
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return ""

    async def _process_monster_asset(
        self, monster_data: Dict[str, Any], fallback_prompt: str
    ) -> MonsterResponse:
        """
        Handles the asset generation (Image) and file saving for a single monster.
        Validates JSON before saving.
        """
        # Determine filename base
        monster_name = monster_data.get("nom", "unknown_monster")
        filename_base = self._get_filename_base(monster_data)

        # VALIDATION STEP: Validate monster JSON
        validation_result = self.validation_service.validate(monster_data)

        if not validation_result.is_valid:
            # Save to defective folder
            logger.warning(f"Monster validation failed: {monster_name}")
            logger.warning(validation_result.get_error_summary())

            defective_path = self.file_manager.save_defective_json(
                filename_base,
                monster_data,
                [
                    {
                        "field": e.field,
                        "error_type": e.error_type,
                        "message": e.message,
                    }
                    for e in validation_result.errors
                ],
            )

            # Still generate image for review purposes
            image_url = await self._generate_image(
                monster_data, fallback_prompt, filename_base
            )

            defective_filename = Path(defective_path).name
            json_path_rel = f"/static/jsons_defective/{defective_filename}"

            # Return response but mark as invalid
            response = MonsterResponse(
                **monster_data,
                image_path=image_url,
                json_path=json_path_rel,
            )
            return response

        # Generate Image
        image_url = await self._generate_image(
            monster_data, fallback_prompt, filename_base
        )

        # Save JSON (only if valid)
        self.file_manager.save_json(filename_base, monster_data)

        # Get relative path for response
        json_path_rel = self.file_manager.get_relative_path(filename_base)

        return MonsterResponse(
            **monster_data, image_path=image_url, json_path=json_path_rel
        )

    async def create_monster(self, prompt: str) -> MonsterResponse:
        """
        Orchestrates the creation of a single monster based on user prompt.
        """
        # Step 1: Generate Profile
        profile_data = await self.gemini_client.generate_monster_profile(prompt)

        # Step 2: Assets & Save (with validation)
        return await self._process_monster_asset(profile_data, prompt)

    async def create_batch_monsters(self, n: int, prompt: str) -> List[MonsterResponse]:
        """
        Generates N monsters in a batch process:
        1. Brainstorm ideas (all at once)
        2. Generate skills (in pairs)
        3. Generate images (sequentially)
        All with validation
        """
        # Step 1: Brainstorming
        monsters_base = await self.gemini_client.generate_batch_brainstorm(n, prompt)

        # Step 2: Skills generation (Chunked)
        monsters_complete = []
        chunk_size = 2
        for i in range(0, len(monsters_base), chunk_size):
            # Add delay between chunks to avoid rate limits
            if i > 0:
                await asyncio.sleep(2)

            chunk = monsters_base[i : i + chunk_size]
            chunk_with_skills = await self.gemini_client.generate_batch_skills(chunk)
            monsters_complete.extend(chunk_with_skills)

        # Step 3: Image generation & Saving (Sequentially for now to be safe, could be gathered)
        result_responses = []
        for monster_data in monsters_complete:
            response = await self._process_monster_asset(monster_data, prompt)
            result_responses.append(response)

        return result_responses
