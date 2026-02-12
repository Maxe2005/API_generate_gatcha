"""
Module: images endpoint

Description:
Routes API pour la gestion des images de monstres
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.models.base import get_db
from app.services.image_service import ImageService
from app.clients.banana import BananaClient
from app.schemas.image import (
    MonsterImageCreate,
    MonsterImageResponse,
    MonsterImageListResponse,
    SetDefaultImageRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images", tags=["Monster Images"])


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    """Dependency pour obtenir le service d'images"""
    banana_client = BananaClient()
    return ImageService(db, banana_client)


@router.post(
    "/generate",
    response_model=MonsterImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Générer une nouvelle image pour un monstre",
    description="Génère une nouvelle image personnalisée pour un monstre existant avec un prompt personnalisé.",
)
async def generate_custom_image(
    request: MonsterImageCreate,
    image_service: ImageService = Depends(get_image_service),
):
    """
    Génère une nouvelle image personnalisée pour un monstre.

    Args:
        request: Données de la requête (monster_id, image_name, custom_prompt)

    Returns:
        MonsterImageResponse: L'image créée avec toutes ses métadonnées

    Raises:
        404: Si le monstre n'existe pas
        500: En cas d'erreur de génération
    """
    try:
        result = await image_service.create_custom_image_for_monster(
            monster_id=request.monster_id,
            image_name=request.image_name,
            custom_prompt=request.custom_prompt,
        )
        logger.info(
            f"Image '{request.image_name}' générée pour le monstre {request.monster_id}"
        )
        return result
    except ValueError as e:
        logger.error(f"Monstre non trouvé: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la génération de l'image: {str(e)}",
        )


@router.get(
    "/{monster_id}",
    response_model=MonsterImageListResponse,
    summary="Récupérer toutes les images d'un monstre",
    description="Récupère la liste de toutes les images d'un monstre avec l'image par défaut.",
)
async def get_monster_images(
    monster_id: str, image_service: ImageService = Depends(get_image_service)
):
    """
    Récupère toutes les images d'un monstre.

    Args:
        monster_id: UUID du monstre

    Returns:
        MonsterImageListResponse: Liste des images avec l'image par défaut

    Raises:
        404: Si le monstre n'existe pas
    """
    try:
        result = image_service.get_monster_images(monster_id)
        return result
    except ValueError as e:
        logger.error(f"Monstre non trouvé: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des images: {str(e)}",
        )


@router.put(
    "/{monster_id}/default",
    response_model=MonsterImageResponse,
    summary="Définir l'image par défaut d'un monstre",
    description="Définit une image comme image par défaut pour un monstre. Retire le flag des autres images.",
)
async def set_default_image(
    monster_id: str,
    request: SetDefaultImageRequest,
    image_service: ImageService = Depends(get_image_service),
):
    """
    Définit une image comme image par défaut pour un monstre.

    Args:
        monster_id: UUID du monstre
        request: ID de l'image à définir comme défaut

    Returns:
        MonsterImageResponse: L'image mise à jour

    Raises:
        404: Si le monstre ou l'image n'existe pas
        400: Si l'image n'appartient pas au monstre
    """
    try:
        result = image_service.set_default_image(monster_id, request.image_id)
        logger.info(
            f"Image {request.image_id} définie comme défaut pour le monstre {monster_id}"
        )
        return result
    except ValueError as e:
        logger.error(f"Erreur de validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST
            if "n'appartient pas" in str(e)
            else status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Erreur lors de la définition de l'image par défaut: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la définition de l'image par défaut: {str(e)}",
        )
