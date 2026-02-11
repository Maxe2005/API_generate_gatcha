"""
Module: metadata

Description:
Schémas de métadonnées pour la gestion du cycle de vie des monstres
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.schemas.monster import MonsterState


class StateTransition(BaseModel):
    """Représente une transition d'état"""

    from_state: Optional[MonsterState] = None
    to_state: MonsterState
    timestamp: datetime
    actor: str = Field(..., description="system|admin|user")
    note: Optional[str] = None


class MonsterMetadata(BaseModel):
    """Métadonnées complètes d'un monstre"""

    monster_id: str = Field(..., description="UUID unique du monstre")
    filename: str = Field(..., description="Nom du fichier JSON")
    state: MonsterState
    created_at: datetime
    updated_at: datetime

    # Génération
    generated_by: str = Field(default="gemini")
    generation_prompt: Optional[str] = None

    # Validation
    is_valid: bool = Field(default=True)
    validation_errors: Optional[List[Dict[str, Any]]] = None

    # Review admin
    reviewed_by: Optional[str] = None
    review_date: Optional[datetime] = None
    review_notes: Optional[str] = None

    # Transmission
    transmitted_at: Optional[datetime] = None
    transmission_attempts: int = Field(default=0)
    last_transmission_error: Optional[str] = None
    invocation_api_id: Optional[str] = None

    # Historique
    history: List[StateTransition] = Field(default_factory=list)

    # Chemins
    metadata: Dict[str, str] = Field(default_factory=dict)


class MonsterWithMetadata(BaseModel):
    """Monstre avec ses métadonnées"""

    metadata: MonsterMetadata
    monster_data: Dict[str, Any]
