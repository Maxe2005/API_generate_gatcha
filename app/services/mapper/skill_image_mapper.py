"""
Module: skill_image_mapper

Description:
Fonctions utilitaires pour mapper les objets SkillImage vers des schémas de sortie.
"""

from app.models.monster.skill_image import SkillImage
from app.schemas.skill_image import SkillImageResponse


def map_skill_image_to_response(image: SkillImage) -> SkillImageResponse:
    return SkillImageResponse(
        id=image.id,  # type: ignore
        skill_id=image.skill_id,  # type: ignore
        source_monster_image_id=image.source_monster_image_id,  # type: ignore
        image_url=image.image_url,  # type: ignore
        prompt=image.prompt,  # type: ignore
        provider=image.provider,  # type: ignore
        model=image.model,  # type: ignore
        is_default=image.is_default,  # type: ignore
        created_at=image.created_at,  # type: ignore
    )
