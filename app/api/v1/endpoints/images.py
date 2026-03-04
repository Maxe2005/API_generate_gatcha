"""
Module: images endpoint

Description:
Routes API pour la gestion des images de monstres
"""

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket
from sqlalchemy.orm import Session
import logging
import uuid
import asyncio
import redis.asyncio as aioredis

from app.models.base import get_db
from app.services.image_service import ImageService
from app.clients.banana import BananaClient
from app.schemas.image import (
    MonsterImageCreate,
    MonsterImageResponse,
    MonsterImageListResponse,
    SetDefaultImageRequest,
    RenameImageRequest,
)
from app.services.tasks import generate_custom_image
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/images")


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    """Dependency pour obtenir le service d'images"""
    banana_client = BananaClient()
    return ImageService(db, banana_client)


@router.post(
    "/generate",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Générer une nouvelle image pour un monstre",
    description="Génère une nouvelle image personnalisée pour un monstre existant avec un prompt personnalisé en arrière-plan (Celery).",
)
async def generate_custom_image_endpoint(
    request: MonsterImageCreate,
):
    """
    Génère une nouvelle image personnalisée pour un monstre de manière asynchrone.
    Lance la génération en tâche de fond (Celery) et retourne un batch_id pour le suivi.

    Args:
        request: Données de la requête (monster_id, image_name, custom_prompt, model)

    Returns:
        dict: {"batch_id": batch_id} - À utiliser pour se connecter au WebSocket /ws/{batch_id}
    """
    batch_id = str(uuid.uuid4())
    logger.info(
        f"Lancement de la génération d'image: batch_id={batch_id}, monster_id={request.monster_id}, image_name={request.image_name}, model={request.model}"
    )
    generate_custom_image.delay(  # pyright: ignore[reportFunctionMemberAccess]
        batch_id,
        request.monster_id,
        request.image_name,
        request.custom_prompt,
        request.model,
    )
    return {"batch_id": batch_id}


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


@router.patch(
    "/{monster_id}/{image_id}/rename",
    response_model=MonsterImageResponse,
    summary="Renommer une image d'un monstre",
    description="Renomme une image existante d'un monstre.",
)
async def rename_image(
    monster_id: str,
    image_id: int,
    request: RenameImageRequest,
    image_service: ImageService = Depends(get_image_service),
):
    """
    Renomme une image d'un monstre.

    Args:
        monster_id: UUID du monstre
        image_id: ID de l'image à renommer
        request: Nouveau nom de l'image

    Returns:
        MonsterImageResponse: L'image mise à jour

    Raises:
        404: Si le monstre ou l'image n'existe pas
        400: Si l'image n'appartient pas au monstre
    """
    try:
        result = image_service.rename_image(monster_id, image_id, request.new_name)
        logger.info(f"Image {image_id} renommée en '{request.new_name}'")
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
        logger.error(f"Erreur lors du renommage de l'image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors du renommage de l'image: {str(e)}",
        )


@router.websocket("/ws/{batch_id}")
async def websocket_image_generation(websocket: WebSocket, batch_id: str):
    """
    WebSocket pour tracker la génération d'une image personnalisée.
    Se connecte à ce WebSocket après avoir reçu un batch_id de la route /generate.

    Args:
        websocket: Connexion WebSocket
        batch_id: ID du batch de génération
    """
    settings = get_settings()
    await websocket.accept()
    logger.info(f"WebSocket connecté pour batch_id={batch_id}")
    redis = await aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0", decode_responses=True
    )
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"batch:{batch_id}")
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=1.0
            )
            if message and message["type"] == "message":
                msg = message["data"]
                logger.info(f"Envoi WebSocket batch_id={batch_id} : {msg[:100]}")
                await websocket.send_text(msg)
                if msg == "Génération terminée":
                    break
            await asyncio.sleep(0.1)
    finally:
        await pubsub.unsubscribe(f"batch:{batch_id}")
        await pubsub.close()
        await redis.close()
    await websocket.close()
    logger.info(f"WebSocket fermé pour batch_id={batch_id}")
