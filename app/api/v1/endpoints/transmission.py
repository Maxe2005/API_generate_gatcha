"""
Transmission endpoints for sending monsters to invocation API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from app.services.transmission_service import TransmissionService
from app.core.config import get_settings
from app.models.base import get_db

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


def get_transmission_service(db: Session = Depends(get_db)) -> TransmissionService:
    """Dependency injection"""
    return TransmissionService(db, invocation_api_url=settings.INVOCATION_API_URL)


@router.post("/transmit/{monster_id}")
async def transmit_monster(
    monster_id: str,
    force: bool = False,
    service: TransmissionService = Depends(get_transmission_service),
):
    """
    Transmet un monstre approuvé vers l'API d'invocation.

    - Le monstre doit être en état APPROVED (sauf si force=true)
    - Après transmission réussie, passe en état TRANSMITTED
    - Retry automatique en cas d'échec
    """
    try:
        result = await service.transmit_monster(monster_id, force)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error transmitting monster {monster_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Transmission failed: {str(e)}")


@router.post("/transmit-batch")
async def transmit_batch(
    max_count: int = None,
    service: TransmissionService = Depends(get_transmission_service),
):
    """
    Transmet tous les monstres approuvés en batch.

    - **max_count**: Nombre maximum à transmettre (optionnel)

    Retourne un rapport détaillé avec succès et échecs.
    """
    try:
        result = await service.transmit_all_approved(max_count)
        return result
    except Exception as e:
        logger.error(f"Error in batch transmission: {e}")
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/health-check")
async def health_check(
    service: TransmissionService = Depends(get_transmission_service),
):
    """Vérifie la disponibilité de l'API d'invocation"""
    try:
        result = await service.health_check()
        return result
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
