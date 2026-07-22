"""
Module: skill_images endpoint

Description:
Routes API pour la génération et la gestion des cartes de compétence.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
import logging
import uuid

from app.models.base import get_db
from app.core.security import require_auth
from app.services.skill_image_service import SkillImageService
from app.clients.image_provider_factory import get_image_client
from app.schemas.skill_image import (
    SkillImageCreate,
    SkillImageListResponse,
    SkillImageResponse,
    SetDefaultSkillImageRequest,
)
from app.services.tasks import generate_skill_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills/images")


def get_skill_image_service(db: Session = Depends(get_db)) -> SkillImageService:
    """Dependency pour obtenir le service de cartes de compétence"""
    image_client = get_image_client()
    return SkillImageService(db, image_client)


@router.post(
    "/generate",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Générer une nouvelle carte de compétence",
    description=(
        "Génère une nouvelle carte de compétence en arrière-plan (Celery), en utilisant "
        "l'image par défaut actuelle du monstre parent comme référence visuelle. "
        "Suivre la progression via le WebSocket existant "
        "/api/v1/monsters/images/ws/{batch_id} (relais générique, indépendant du contenu du batch)."
    ),
    dependencies=[Depends(require_auth)],
)
async def generate_skill_image_endpoint(request: SkillImageCreate):
    """
    Lance la génération d'une carte de compétence de manière asynchrone et
    retourne un batch_id pour le suivi.
    """
    batch_id = str(uuid.uuid4())
    logger.info(
        f"Lancement de la génération de carte de compétence: batch_id={batch_id}, "
        f"skill_id={request.skill_id}, provider={request.provider.value}, model={request.model}"
    )
    generate_skill_image.delay(  # pyright: ignore[reportFunctionMemberAccess]
        batch_id,
        request.skill_id,
        request.custom_prompt,
        request.model,
        request.provider.value,
    )
    return {"batch_id": batch_id}


@router.get(
    "/{skill_id}",
    response_model=SkillImageListResponse,
    summary="Récupérer les cartes de compétence d'une compétence",
    description=(
        "Par défaut, retourne les cartes générées à partir de l'image de monstre "
        "ACTUELLEMENT par défaut (ne mélange jamais des cartes issues d'anciennes "
        "images de référence). Passer `monster_image_id` pour cibler explicitement "
        "un autre groupe."
    ),
)
async def get_skill_images(
    skill_id: int,
    monster_image_id: int | None = Query(
        default=None,
        description="Cible explicitement un groupe précis (image de monstre source) au lieu du défaut courant",
    ),
    skill_image_service: SkillImageService = Depends(get_skill_image_service),
):
    try:
        if monster_image_id is not None:
            return skill_image_service.get_skill_card_images_for_source(skill_id, monster_image_id)
        return skill_image_service.get_skill_card_images_for_current_default(skill_id)
    except ValueError as e:
        logger.error(f"Compétence non trouvée: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des cartes de compétence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des cartes de compétence: {str(e)}",
        )


@router.put(
    "/{skill_id}/default",
    response_model=SkillImageResponse,
    summary="Définir la carte de compétence par défaut",
    description="Définit une carte comme carte par défaut au sein de son groupe (même image de monstre source).",
    dependencies=[Depends(require_auth)],
)
async def set_default_skill_image(
    skill_id: int,
    request: SetDefaultSkillImageRequest,
    skill_image_service: SkillImageService = Depends(get_skill_image_service),
):
    try:
        result = skill_image_service.set_default_image(skill_id, request.image_id)
        logger.info(f"Carte {request.image_id} définie comme défaut pour la compétence {skill_id}")
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
        logger.error(f"Erreur lors de la définition de la carte par défaut: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la définition de la carte par défaut: {str(e)}",
        )
