"""
Module: image_mapper

Description:
Fonctions utilitaires pour mapper les objets de données d'image vers des schémas de sortie.
"""

from app.models.monster_image_model import MonsterImage
from app.schemas.image import MonsterImageResponse


def map_image_to_response(image: MonsterImage) -> MonsterImageResponse:
    return MonsterImageResponse(
        id=image.id, #  type: ignore
        image_url=image.image_url, #  type: ignore
        created_at=image.created_at, #  type: ignore
        image_name=image.image_name, #  type: ignore
        prompt=image.prompt, #  type: ignore
        is_default=image.is_default, #  type: ignore
    )
