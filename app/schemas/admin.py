"""
Module: admin

Description:
Schémas pour l'API d'administration des monstres
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.schemas.monster import MonsterState, TransitionAction
from app.schemas.metadata import MonsterMetadata


class MonsterListFilter(BaseModel):
    """Filtres pour la liste des monstres"""

    state: Optional[MonsterState] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    sort_by: str = Field(default="created_at")
    order: str = Field(default="desc", pattern="^(asc|desc)$")
    search: Optional[str] = None


class MonsterSummary(BaseModel):
    """Résumé d'un monstre pour la liste"""

    monster_id: str
    filename: str
    name: str
    element: str
    rank: str
    state: MonsterState
    created_at: datetime
    updated_at: datetime
    is_valid: bool
    review_notes: Optional[str] = None


class MonsterDetail(BaseModel):
    """Détails complets d'un monstre"""

    metadata: MonsterMetadata
    monster_data: Dict[str, Any]
    image_url: Optional[str] = None
    validation_report: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    """Requête pour reviewer un monstre"""

    action: TransitionAction
    notes: Optional[str] = Field(None, max_length=1000)
    corrected_data: Optional[Dict[str, Any]] = None


class CorrectionRequest(BaseModel):
    """Requête pour corriger un monstre défectueux"""

    corrected_data: Dict[str, Any]
    notes: Optional[str] = None


class TransmitRequest(BaseModel):
    """Requête pour transmettre un monstre"""

    monster_id: Optional[str] = None
    force: bool = Field(default=False, description="Force la retransmission")


class DashboardStats(BaseModel):
    """Statistiques du dashboard"""

    total_monsters: int
    by_state: Dict[str, int]
    transmission_rate: float
    avg_review_time_hours: Optional[float] = None
    recent_activity: List[Dict[str, Any]]


class ConfigUpdate(BaseModel):
    """Mise à jour de la configuration"""

    auto_transmit: Optional[bool] = None
    invocation_api_url: Optional[str] = None
    max_retry_attempts: Optional[int] = Field(None, ge=1, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=300)
