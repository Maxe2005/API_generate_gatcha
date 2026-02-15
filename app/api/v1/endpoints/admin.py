"""
Admin endpoints for managing monster lifecycle
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from app.services.admin_service import AdminService
from app.schemas.admin import (
    MonsterSummary,
    MonsterDetail,
    ReviewRequest,
    CorrectionRequest,
    DashboardStats,
)
from app.core.constants import MonsterStateEnum
from app.services.validation_service import MonsterValidationService
from app.models.base import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

validation_service = MonsterValidationService()


# ===== Dependency Injection =====


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    """Dependency injection"""
    return AdminService(db)


# ===== New Lifecycle Management Endpoints =====


@router.get("/monsters", response_model=List[MonsterSummary])
async def list_monsters(
    state: Optional[MonsterStateEnum] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    service: AdminService = Depends(get_admin_service),
):
    """
    Liste tous les monstres avec filtres optionnels.

    - **state**: Filtrer par état (optionnel)
    - **limit**: Nombre max de résultats (1-200)
    - **offset**: Pagination
    - **sort_by**: Champ de tri
    - **order**: Ordre (asc|desc)
    """
    try:
        return service.list_monsters(state, limit, offset, sort_by, order)
    except Exception as e:
        logger.error(f"Error listing monsters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monsters/{monster_id}", response_model=MonsterDetail)
async def get_monster_detail(
    monster_id: str, service: AdminService = Depends(get_admin_service)
):
    """
    Récupère les détails complets d'un monstre.

    Inclut :
    - Métadonnées complètes
    - Données du monstre
    - Historique des transitions
    - Rapport de validation si erreurs
    """
    try:
        detail = service.get_monster_detail(monster_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Monster not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monsters/{monster_id}/history")
async def get_monster_history(
    monster_id: str, service: AdminService = Depends(get_admin_service)
):
    """Récupère l'historique complet des transitions d'un monstre"""
    try:
        monster = service.state_repository.get(monster_id)
        if not monster:
            raise HTTPException(status_code=404, detail="Monster not found")

        return {
            "monster_id": monster_id,
            "current_state": monster.metadata.state,
            "history": [
                {
                    "from_state": t.from_state,
                    "to_state": t.to_state,
                    "timestamp": t.timestamp,
                    "actor": t.actor,
                    "note": t.note,
                }
                for t in monster.metadata.history
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monsters/{monster_id}/review")
async def review_monster(
    monster_id: str,
    request: ReviewRequest,
    service: AdminService = Depends(get_admin_service),
):
    """
    Review un monstre (approve ou reject).

    - **action**: "approve" ou "reject"
    - **notes**: Notes optionnelles
    - **corrected_data**: Données corrigées si nécessaire
    """
    try:
        metadata = service.review_monster(
            monster_id,
            request.action,
            request.notes,
            request.corrected_data,
            admin_name=request.admin_name,
        )

        return {
            "status": "success",
            "monster_id": monster_id,
            "new_state": metadata.state,
            "message": f"Monster {request.action.value}d successfully",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reviewing monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monsters/{monster_id}/correct")
async def correct_defective_monster(
    monster_id: str,
    request: CorrectionRequest,
    service: AdminService = Depends(get_admin_service),
):
    """
    Corrige un monstre défectueux.

    Le monstre doit être en état DEFECTIVE.
    Après correction, il passe en PENDING_REVIEW.
    """
    try:
        metadata = service.correct_defective(
            monster_id, request.corrected_data, request.notes, admin_name="admin"
        )

        return {
            "status": "success",
            "monster_id": monster_id,
            "new_state": metadata.state,
            "message": "Monster corrected and moved to PENDING_REVIEW",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error correcting monster {monster_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(service: AdminService = Depends(get_admin_service)):
    """
    Récupère les statistiques du dashboard admin.

    Inclut :
    - Nombre total de monstres
    - Répartition par état
    - Taux de transmission
    - Temps moyen de review
    - Activité récente
    """
    try:
        return service.get_dashboard_stats()
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monsters/process-generated")
async def process_generated_monsters(
    service: AdminService = Depends(get_admin_service),
):
    """
    Traite tous les monstres en état GENERATED.

    Pour chaque monstre:
    - Valide les données
    - Si valide: déplace vers PENDING_REVIEW
    - Si invalide: déplace vers DEFECTIVE avec les erreurs

    Utile pour:
    - Traiter les monstres bloqués en GENERATED
    - Gérer les imports externes de monstres
    - Corriger des échecs de transition automatique
    """
    try:
        result = service.process_generated_monsters()

        return {
            "status": "success",
            "total_processed": result["total_processed"],
            "moved_to_pending_review": result["moved_to_pending_review"],
            "moved_to_defective": result["moved_to_defective"],
            "details": result["details"],
        }
    except Exception as e:
        logger.error(f"Error processing generated monsters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validation-rules")
async def get_validation_rules():
    """
    Get all validation rules for reference
    Useful for frontend to know constraints
    """
    from app.core.config import ValidationRules

    return {
        "valid_stats": list(ValidationRules.VALID_STATS),
        "valid_elements": list(ValidationRules.VALID_ELEMENTS),
        "valid_ranks": list(ValidationRules.VALID_RANKS),
        "stat_limits": {
            k: {"min": v[0], "max": v[1]}
            for k, v in ValidationRules.STAT_LIMITS.items()
        },
        "skill_limits": {
            k: {"min": v[0], "max": v[1]}
            for k, v in ValidationRules.SKILL_LIMITS.items()
        },
        "lvl_max": ValidationRules.LVL_MAX,
        "max_card_description_length": ValidationRules.MAX_CARD_DESCRIPTION_LENGTH,
    }
