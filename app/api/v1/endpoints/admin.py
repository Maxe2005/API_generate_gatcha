"""
Admin endpoints for managing monster lifecycle
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
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
from app.schemas.monster import MonsterState
from app.utils.file_manager import FileManager
from app.services.validation_service import MonsterValidationService
from app.models.base import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

# Legacy services for compatibility
file_manager = FileManager()
validation_service = MonsterValidationService()


# ===== Dependency Injection =====


def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    """Dependency injection"""
    return AdminService(db)


# ===== New Lifecycle Management Endpoints =====


@router.get("/monsters", response_model=List[MonsterSummary])
async def list_monsters(
    state: Optional[MonsterState] = Query(None),
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
        monster = service.repository.get(monster_id)
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
            admin_name="admin",
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


# ===== Legacy Endpoints (kept for backward compatibility) =====


class DefectiveJsonSummary(BaseModel):
    """Summary of a defective JSON"""

    filename: str
    created_at: str
    status: str
    error_count: int
    monster_name: str


class ValidationErrorDetail(BaseModel):
    """Detail of a validation error"""

    field: str
    error_type: str
    message: str


class DefectiveJsonDetail(BaseModel):
    """Full details of a defective JSON with errors"""

    filename: str
    created_at: str
    status: str
    monster_data: Dict[str, Any]
    validation_errors: List[ValidationErrorDetail]
    notes: str


class ApproveDefectiveRequest(BaseModel):
    """Request to approve a corrected defective JSON"""

    corrected_data: Dict[str, Any] = Field(..., description="Corrected monster data")
    notes: str = Field(default="", description="Optional notes from admin")


class RejectDefectiveRequest(BaseModel):
    """Request to reject a defective JSON"""

    reason: str = Field(..., description="Reason for rejection")


# ===== Endpoints =====


@router.get("/defective", response_model=List[DefectiveJsonSummary])
async def list_defective_jsons():
    """
    List all defective monster JSONs waiting for review
    """
    try:
        defective_list = file_manager.list_defective_jsons()
        return defective_list
    except Exception as e:
        logger.error(f"Error listing defective JSONs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/defective/{filename}", response_model=DefectiveJsonDetail)
async def get_defective_json(filename: str):
    """
    Get full details of a defective JSON including errors
    """
    try:
        if not filename.endswith(".json"):
            filename += ".json"

        defective_data = file_manager.get_defective_json(filename)

        if not defective_data:
            raise HTTPException(status_code=404, detail="Defective JSON not found")

        return DefectiveJsonDetail(
            filename=filename,
            created_at=defective_data.get("created_at", ""),
            status=defective_data.get("status", ""),
            monster_data=defective_data.get("monster_data", {}),
            validation_errors=defective_data.get("validation_errors", []),
            notes=defective_data.get("notes", ""),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching defective JSON {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/defective/{filename}/approve")
async def approve_defective_json(filename: str, request: ApproveDefectiveRequest):
    """
    Approve and correct a defective JSON
    The corrected data will be validated and moved to valid folder if approved
    """
    try:
        if not filename.endswith(".json"):
            filename += ".json"

        # Validate the corrected data
        validation_result = validation_service.validate(request.corrected_data)

        if not validation_result.is_valid:
            # Return validation errors without moving
            return {
                "status": "rejected",
                "reason": "Corrected data still has validation errors",
                "errors": validation_result.to_dict()["errors"],
            }

        # Move from defective to valid folder
        new_path = file_manager.move_defective_to_valid(
            filename, request.corrected_data
        )

        logger.info(f"Defective JSON approved and moved: {filename} -> {new_path}")

        return {
            "status": "approved",
            "message": f"Monster approved and saved to valid folder",
            "new_path": new_path,
            "notes": request.notes,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving defective JSON {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/defective/{filename}/reject")
async def reject_defective_json(filename: str, request: RejectDefectiveRequest):
    """
    Reject and delete a defective JSON
    """
    try:
        if not filename.endswith(".json"):
            filename += ".json"

        success = file_manager.delete_defective_json(filename)

        if not success:
            raise HTTPException(status_code=404, detail="Defective JSON not found")

        logger.info(
            f"Defective JSON rejected and deleted: {filename}. Reason: {request.reason}"
        )

        return {
            "status": "rejected",
            "message": f"Monster deleted",
            "reason": request.reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting defective JSON {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/defective/{filename}/update")
async def update_defective_json(filename: str, request: ApproveDefectiveRequest):
    """
    Update a defective JSON with corrections
    Does not validate yet - allows admin to make multiple updates before approval
    """
    try:
        if not filename.endswith(".json"):
            filename += ".json"

        updated_path = file_manager.update_defective_json(
            filename,
            request.corrected_data,
            new_status="pending_review",
            notes=request.notes,
        )

        if not updated_path:
            raise HTTPException(status_code=404, detail="Defective JSON not found")

        logger.info(f"Defective JSON updated: {filename}")

        return {
            "status": "updated",
            "message": "Monster data updated",
            "path": updated_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating defective JSON {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/defective/{filename}/validate")
async def validate_defective_json(filename: str):
    """
    Validate a defective JSON without approving it
    Useful to check if corrections are valid
    """
    try:
        if not filename.endswith(".json"):
            filename += ".json"

        defective_data = file_manager.get_defective_json(filename)

        if not defective_data:
            raise HTTPException(status_code=404, detail="Defective JSON not found")

        monster_data = defective_data.get("monster_data", {})
        validation_result = validation_service.validate(monster_data)

        return {
            "filename": filename,
            "is_valid": validation_result.is_valid,
            "validation": validation_result.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating defective JSON {filename}: {e}")
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
