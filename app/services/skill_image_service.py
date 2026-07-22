"""
Module: skill_image_service

Description:
Service pour générer et gérer les cartes de compétence (images IA illustrant
une compétence, en conservant l'identité visuelle du monstre). Le client de
génération d'images est injecté (Gemini ou fal.ai, voir
app/clients/image_provider_factory.py) — ce service est agnostique du provider.
"""

import logging

import httpx
from sqlalchemy.orm import Session

from app.clients.fal_client import FalImageClient
from app.clients.image_generation_client import ImageGenerationClient
from app.core.prompts import GatchaPrompts
from app.repositories.monster.skill_repository import SkillRepository
from app.repositories.monster_image_repository import MonsterImageRepository
from app.repositories.skill_image_repository import SkillImageRepository
from app.schemas.skill_image import SkillImageListResponse, SkillImageResponse
from app.services.mapper.skill_image_mapper import map_skill_image_to_response
from app.utils.send_messages_utils import run_async, send_error_message

logger = logging.getLogger(__name__)


class SkillImageService:
    """
    Service pour gérer la génération et la consultation des cartes de compétence.
    """

    def __init__(self, db: Session, image_client: ImageGenerationClient | FalImageClient):
        self.db = db
        self.skill_repo = SkillRepository(db)
        self.monster_image_repo = MonsterImageRepository(db)
        self.skill_image_repo = SkillImageRepository(db)
        self.image_client = image_client

    async def create_skill_card_image(
        self,
        skill_id: int,
        custom_prompt: str | None,
        provider: str,
        model: str | None,
    ) -> SkillImageResponse | None:
        """
        Génère une nouvelle carte de compétence pour une compétence existante,
        en utilisant l'image par défaut actuelle du monstre parent comme
        référence visuelle (image-to-image).

        Args:
            skill_id: ID de la compétence
            custom_prompt: Prompt personnalisé (généré depuis la compétence si absent)
            provider: Provider IA utilisé (persisté avec la carte, pour traçabilité)
            model: Modèle à utiliser (défaut du provider si absent)

        Returns:
            SkillImageResponse: La carte créée, ou None en cas d'erreur

        Raises:
            ValueError: Si la compétence n'existe pas ou si le monstre parent
                n'a pas encore d'image par défaut
        """
        skill = self.skill_repo.get_by_id(skill_id)
        if not skill:
            raise ValueError(f"Compétence avec ID {skill_id} non trouvée")

        monster = skill.monster
        source_image = self.monster_image_repo.get_default_image(int(monster.id))  # type: ignore
        if not source_image:
            raise ValueError(
                f"Le monstre {monster.id} n'a pas d'image par défaut : "
                "impossible de générer une carte de compétence sans référence visuelle"
            )

        prompt = custom_prompt or GatchaPrompts.SKILL_CARD_IMAGE(
            monster_name=str(monster.name),
            monster_element=str(monster.element.value)
            if hasattr(monster.element, "value")
            else str(monster.element),
            skill_name=str(skill.name),
            skill_description=str(skill.description),
        )

        filename_base = (
            "".join(c for c in f"{monster.name}_{skill.name}".lower() if c.isalnum() or c == "_")
            or f"skill_{skill_id}"
        )

        logger.info(
            f"Génération d'une carte de compétence pour skill_id={skill_id} "
            f"(monstre={monster.id}, source_monster_image_id={source_image.id}, provider={provider})"
        )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(str(source_image.image_url))
                response.raise_for_status()
                reference_bytes = response.content

            result = await self.image_client.generate_pixel_art(
                prompt,
                filename_base,
                model,
                reference_image_bytes=reference_bytes,
            )
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la carte de compétence : {e}")
            run_async(
                send_error_message(str(skill_id), f"Erreur génération carte de compétence: {e}")
            )
            return None

        db_image = self.skill_image_repo.create_image(
            skill_id=skill_id,
            source_monster_image_id=int(source_image.id),  # type: ignore
            image_url=result["image_url"],
            prompt=prompt,
            provider=provider,
            model=model,
            is_default=False,
            raw_image_key=result.get("raw_image_key"),
        )

        return map_skill_image_to_response(db_image)

    def get_skill_card_images_for_current_default(self, skill_id: int) -> SkillImageListResponse:
        """
        Récupère les cartes de compétence correspondant à l'image de monstre
        ACTUELLEMENT par défaut. C'est le comportement attendu lors de tout
        affichage : ne jamais mélanger des cartes produites depuis d'anciennes
        images de référence avec l'image par défaut courante.

        Raises:
            ValueError: Si la compétence n'existe pas, ou si le monstre parent
                n'a pas d'image par défaut
        """
        skill = self.skill_repo.get_by_id(skill_id)
        if not skill:
            raise ValueError(f"Compétence avec ID {skill_id} non trouvée")

        source_image = self.monster_image_repo.get_default_image(int(skill.monster_id))  # type: ignore
        if not source_image:
            return SkillImageListResponse(
                images=[], default_image=None, source_monster_image_id=None
            )

        return self.get_skill_card_images_for_source(skill_id, int(source_image.id))  # type: ignore

    def get_skill_card_images_for_source(
        self, skill_id: int, source_monster_image_id: int
    ) -> SkillImageListResponse:
        """Récupère les cartes de compétence d'un groupe (skill_id, source_monster_image_id) donné."""
        db_images = self.skill_image_repo.get_images_by_skill_and_source(
            skill_id, source_monster_image_id
        )
        images = [map_skill_image_to_response(img) for img in db_images]
        default_image = next((img for img in images if img.is_default), None)

        return SkillImageListResponse(
            images=images,
            default_image=default_image,
            source_monster_image_id=source_monster_image_id,
        )

    def set_default_image(self, skill_id: int, image_id: int) -> SkillImageResponse:
        """Définit une carte comme carte par défaut au sein de son groupe."""
        db_image = self.skill_image_repo.set_default_image(image_id=image_id, skill_id=skill_id)
        return map_skill_image_to_response(db_image)
