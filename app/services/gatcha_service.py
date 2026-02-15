import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
import logging
from sqlalchemy.orm import Session

from app.clients.gemini import GeminiClient
from app.clients.banana import BananaClient
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.structure_repository import StructureRepository
from app.schemas.monster import MonsterResponse
from app.core.constants import MonsterStateEnum
from app.schemas.metadata import MonsterMetadata
from app.repositories.monster_image_repository import MonsterImageRepository
from app.services.validation_service import MonsterValidationService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GatchaService:
    def __init__(self, db: Session):
        self.gemini_client = GeminiClient()
        self.banana_client = BananaClient()
        self.validation_service = MonsterValidationService()
        self.state_repository = MonsterStateRepository(db)
        self.structure_repository = StructureRepository(db)
        self.image_repository = MonsterImageRepository(db)
        self.settings = get_settings()
        self.db = db

    def _get_filename_base(self, monster_data: Dict[str, Any]) -> str:
        """Build a safe filename base from monster name."""
        monster_name = monster_data.get("nom", "unknown_monster")
        # Simple sanitization: lowercase, remove spaces and special chars
        filename_base = (
            "".join(c for c in monster_name.lower() if c.isalnum())
            or f"monster_{uuid.uuid4().hex[:8]}"
        )
        return filename_base

    async def _generate_image(
        self, monster_data: Dict[str, Any], fallback_prompt: str, filename_base: str
    ) -> tuple[str, str]:
        """
        Generate image for a monster, safe-failing on errors.

        Returns:
            tuple: (image_url, raw_image_key)
        """
        visual_prompt = monster_data.get("description_visuelle", fallback_prompt)
        try:
            result = await self.banana_client.generate_pixel_art(
                visual_prompt, filename_base
            )
            return result["image_url"], result["raw_image_key"]
        except Exception as e:
            logger.error(f"Failed to generate image: {e}")
            return "", ""

    async def _process_monster_asset(
        self, monster_data: Dict[str, Any], fallback_prompt: str
    ) -> MonsterResponse:
        """
        Handles the asset generation (Image) and PostgreSQL persistence for a single monster.
        Validates JSON before saving.
        """
        filename = self._get_filename_base(monster_data)
        monster_id = str(uuid.uuid4())

        # VALIDATION STEP: Validate monster JSON
        validation_result = self.validation_service.validate(monster_data)

        # Generate image even if invalid for review
        image_url, raw_image_key = await self._generate_image(
            monster_data, fallback_prompt, filename
        )
        monster_data["ImageUrl"] = image_url

        # VALIDATION STEP: Validate ImageUrl presence and format
        image_url_validation = self.validation_service.validate_image_url(image_url)

        validation_errors = [
            {
                "field": e.field,
                "error_type": e.error_type,
                "message": e.message,
            }
            for e in validation_result.errors
        ]

        # Add image URL validation errors if any
        if not image_url_validation.is_valid:
            validation_errors.extend(
                [
                    {
                        "field": e.field,
                        "error_type": e.error_type,
                        "message": e.message,
                    }
                    for e in image_url_validation.errors
                ]
            )
            validation_result.is_valid = False

        initial_state = MonsterStateEnum.GENERATED

        now = datetime.now(timezone.utc)

        metadata = MonsterMetadata(
            monster_id=monster_id,
            state=initial_state,
            created_at=now,
            updated_at=now,
            generated_by="gemini",
            generation_prompt=fallback_prompt,
            is_valid=validation_result.is_valid,
            validation_errors=validation_errors if validation_errors else None,
        )

        # Persist initial monster state
        self.state_repository.save(metadata, monster_data)
        self.structure_repository.add_transition(
            monster_id,
            None,
            initial_state,
            actor="system",
            note="Created",
        )

        # Auto-transition valid monsters to PENDING_REVIEW
        if validation_result.is_valid:
            self.structure_repository.move_to_state(
                monster_id,
                MonsterStateEnum.PENDING_REVIEW,
                actor="system",
                note="Auto-transition: monster validation passed",
            )
            metadata.state = MonsterStateEnum.PENDING_REVIEW
            metadata.updated_at = datetime.now(timezone.utc)
        else:
            self.structure_repository.move_to_state(
                monster_id,
                MonsterStateEnum.DEFECTIVE,
                actor="system",
                note="Monster marked as defective after validation failure",
            )
            metadata.state = MonsterStateEnum.DEFECTIVE
            metadata.updated_at = datetime.now(timezone.utc)
            logger.warning(
                "Monster validation failed: %s", monster_data.get("nom", "unknown")
            )
            logger.warning(validation_result.get_error_summary())

        return MonsterResponse(**monster_data, image_path=image_url)

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
        logger.info(
            f"🚀 Starting batch generation for {n} monsters (Prompt: '{prompt}')."
        )

        # Step 1: Brainstorming
        logger.info("Step 1/3: Brainstorming concepts...")
        monsters_base = await self.gemini_client.generate_batch_brainstorm(n, prompt)
        logger.info(
            f"✅ Brainstorming complete: {len(monsters_base)} concepts generated."
        )

        # Step 2: Skills generation (Chunked)
        logger.info("Step 2/3: Generating Details & Skills (Chunked)...")
        monsters_complete = []
        chunk_size = 5
        total_base = len(monsters_base)

        for i in range(0, total_base, chunk_size):
            # Progress Log
            chunk_num = (i // chunk_size) + 1
            total_chunks = (total_base + chunk_size - 1) // chunk_size
            percent = int((i / total_base) * 100)
            bar = "▓" * (percent // 5) + "░" * (20 - (percent // 5))
            logger.info(
                f"   Skills Progress: [{bar}] {percent}% (Chunk {chunk_num}/{total_chunks})"
            )

            chunk = monsters_base[i : i + chunk_size]
            chunk_with_skills = await self.gemini_client.generate_batch_skills(chunk)
            monsters_complete.extend(chunk_with_skills)

        logger.info(f"   Skills Progress: [{'▓' * 20}] 100% - Skills generated.")

        # Step 3: Image generation & Saving (Sequentially for now to be safe, could be gathered)
        logger.info("Step 3/3: Generating Images & Saving...")
        result_responses = []
        total_monsters = len(monsters_complete)

        for idx, monster_data in enumerate(monsters_complete, 1):
            # Progress Log
            percent = int(((idx - 1) / total_monsters) * 100)
            bar = "▓" * (percent // 5) + "░" * (20 - (percent // 5))
            monster_name = monster_data.get("nom", "Unknown")
            logger.info(
                f"   Assets Progress: [{bar}] {percent}% - Processing '{monster_name}' ({idx}/{total_monsters})"
            )

            response = await self._process_monster_asset(monster_data, prompt)
            result_responses.append(response)

        logger.info(f"   Assets Progress: [{'▓' * 20}] 100% - Batch Complete.")
        logger.info("🎉 Batch generation finished successfully.")

        return result_responses
