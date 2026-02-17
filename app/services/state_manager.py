"""
Module: state_manager

Description:
Gère les états des monstres et les transitions valides.
Gère la transition spéciale JSON → DB structurée lors du passage à PENDING_REVIEW.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from app.core.constants import MonsterStateEnum
from app.repositories.monster.state_repository import MonsterStateRepository
from app.repositories.monster.transition_repository import TransitionRepository
from app.schemas.metadata import MonsterMetadata, StateTransition
import logging

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Exception levée lors d'une transition invalide"""

    pass


class MonsterStateManager:
    """
    Gère les états des monstres et les transitions valides.
    Respecte le principe Single Responsibility (SOLID).

    Responsabilités :
    - Valider les transitions d'état
    - Enregistrer l'historique des transitions
    - Orchestrer la transition JSON → DB (PENDING_REVIEW)
    """

    def __init__(
        self,
        state_repository: MonsterStateRepository,
        transition_repository: TransitionRepository,
    ):
        self.state_repository = state_repository
        self.transition_repository = transition_repository

    # Définition des transitions valides
    VALID_TRANSITIONS: Dict[MonsterStateEnum, list] = {
        MonsterStateEnum.GENERATED: [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.DEFECTIVE,
        ],
        MonsterStateEnum.DEFECTIVE: [
            MonsterStateEnum.PENDING_REVIEW,
            MonsterStateEnum.REJECTED,
        ],
        MonsterStateEnum.PENDING_REVIEW: [
            MonsterStateEnum.APPROVED,
            MonsterStateEnum.REJECTED,
        ],
        MonsterStateEnum.APPROVED: [
            MonsterStateEnum.TRANSMITTED,
            MonsterStateEnum.PENDING_REVIEW,
        ],
        MonsterStateEnum.TRANSMITTED: [],
        MonsterStateEnum.REJECTED: [],
    }

    # États qui nécessitent des données JSON (avant structuration)
    JSON_STATES = [
        MonsterStateEnum.GENERATED,
        MonsterStateEnum.DEFECTIVE,
    ]

    # États qui nécessitent des données structurées (après structuration)
    STRUCTURED_STATES = [
        MonsterStateEnum.PENDING_REVIEW,
        MonsterStateEnum.APPROVED,
        MonsterStateEnum.TRANSMITTED,
        MonsterStateEnum.REJECTED,
    ]

    def can_transition(
        self, from_state: MonsterStateEnum, to_state: MonsterStateEnum
    ) -> bool:
        """Vérifie si une transition est valide"""
        return to_state in self.VALID_TRANSITIONS.get(from_state, [])

    def transition(
        self,
        metadata: MonsterMetadata,
        to_state: MonsterStateEnum,
        actor: str = "system",
        note: Optional[str] = None,
    ) -> MonsterMetadata:
        """
        Effectue une transition d'état si elle est valide.

        Note : Cette méthode ne gère PAS la transition JSON → DB.
        Pour les transitions vers PENDING_REVIEW, utiliser `transition_to_pending_review()`.

        Args:
            metadata: Métadonnées du monstre
            to_state: État cible
            actor: Qui effectue la transition (system|admin|user)
            note: Note optionnelle

        Returns:
            Métadonnées mises à jour

        Raises:
            StateTransitionError: Si la transition est invalide
        """
        current_state = metadata.state

        if not self.can_transition(current_state, to_state):
            raise StateTransitionError(
                f"Invalid transition from {current_state} to {to_state}"
            )

        # Enregistrer la transition
        transition = StateTransition(
            from_state=current_state,
            to_state=to_state,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            note=note,
        )

        # Mettre à jour les métadonnées
        metadata.state = to_state
        metadata.updated_at = datetime.now(timezone.utc)
        metadata.history.append(transition)

        logger.info(
            f"Monster {metadata.monster_id}: {current_state} → {to_state} (by {actor})"
        )

        return metadata

    def perform_transition(
        self,
        metadata: MonsterMetadata,
        to_state: MonsterStateEnum,
        monster_data: Optional[Dict[str, Any]] = None,
        actor: str = "system",
        note: Optional[str] = None,
    ) -> MonsterMetadata:
        """
        Orchestration complète d'une transition d'état :
        - Valide la transition
        - Met à jour l'historique
        - Persiste les métadonnées
        - Gère la structuration JSON → DB si besoin
        """
        # 1. Valider et appliquer la transition métier (métadonnées)
        updated_metadata = self.transition(metadata, to_state, actor=actor, note=note)

        # 2. Persister les métadonnées (toujours)
        self.state_repository.save(updated_metadata, monster_data)

        # 3. si transition vers PENDING_REVIEW, orchestrer la transition JSON → DB structurée
        if to_state == MonsterStateEnum.PENDING_REVIEW:
            monster_state = self.state_repository.get_db_object(updated_metadata.monster_id)
            data: Dict[str, Any] = monster_state.monster_data  # type: ignore
            if not data :
                logger.error("Monster data is required for database transition")
                raise ValueError("Monster data is required for database transition")
            self.transition_repository.create_structured_monster_from_json(
                monster_state, data
            )

        return updated_metadata

    def get_next_states(self, current_state: MonsterStateEnum) -> list:
        """Retourne les états possibles depuis l'état actuel"""
        return self.VALID_TRANSITIONS.get(current_state, [])

    def is_final_state(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état est final"""
        return len(self.VALID_TRANSITIONS.get(state, [])) == 0

    def requires_json_data(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état nécessite des données JSON"""
        return state in self.JSON_STATES

    def requires_structured_data(self, state: MonsterStateEnum) -> bool:
        """Vérifie si un état nécessite des données structurées"""
        return state in self.STRUCTURED_STATES
